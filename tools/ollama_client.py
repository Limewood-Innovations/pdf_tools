# -*- coding: utf-8 -*-
"""IBAN and BIC extraction using Ollama vision model.

This module provides functionality to extract IBAN and BIC information from
PDF documents using a locally hosted Ollama vision model (e.g., llava).
"""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass
class IbanExtractionResult:
    """Result of IBAN/BIC extraction from document.

    Attributes:
        iban_raw: IBAN as it appears in the document (may include spaces).
        iban: Normalized IBAN (uppercase, no spaces).
        bic_raw: BIC as it appears in the document.
        bic: Normalized BIC (uppercase, no spaces).
        confidence: Confidence score from 0.0 to 1.0.
        evidence_excerpt: Short excerpt showing where values were found.
    """

    iban_raw: Optional[str]
    iban: Optional[str]
    bic_raw: Optional[str]
    bic: Optional[str]
    confidence: float
    evidence_excerpt: Optional[str]


# System prompt for IBAN/BIC extraction from document images
LLM_SYSTEM_PROMPT = """You are a precise information extraction engine. 
Extract banking identifiers from document images.  
Follow the schema exactly. 
Do not include any extra commentary.  
If uncertain, return null for the field. 
Never hallucinate.

TASK:
From the provided document image, extract the best candidate IBAN and BIC.
Return a single JSON object.

REQUIREMENTS:
1) SCOPE
   - Extract up to ONE IBAN and ONE BIC most relevant to payments (ignore examples, footers, unrelated references).
   - Consider common labels: "IBAN", "IBAN-Nr.", "IBAN:", "Kontonummer (IBAN)", "International Bank Account Number",
     "BIC", "SWIFT", "SWIFT/BIC", "SWIFT-Code".
   - Handle OCR noise: extra spaces, line breaks, dots, non-breaking spaces.

2) IBAN RULES
   - Pattern (loose): country code A–Z (2 letters), 2 check digits (0–9), then up to 30 alphanumerics.
   - Normalize by removing spaces, tabs, newlines, hyphens, and dots; uppercase all letters.

3) BIC RULES
   - Pattern (strict): 8 or 11 characters.
     Regex: `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$`
   - Normalize by uppercasing; remove spaces and punctuation if present.
   - If both 8- and 11-char variants appear for the same bank, prefer the 11-char version.

4) DISAMBIGUATION
   - If multiple candidates exist, choose the one closest to explicit payment context (e.g., headings "Zahlung", "Überweisung", "Invoice", "Payment details").
   - Prefer IBAN/BIC pairs that appear near each other.
   - If nothing plausible is found, set fields to null.

5) OUTPUT FORMAT (JSON ONLY)
{
  "iban_raw": string | null,      // as it appears in the document (may include spaces)
  "IBAN": string | null,          // e.g., "AT771234456778911234"
  "BIC_raw": string | null,       // as it appears in the document
  "BIC": string | null,           // uppercase, no spaces
  "confidence": number,           // 0.0–1.0 overall confidence in the extracted pair
  "evidence_excerpt": string | null
}

CONSTRAINTS:
- Output MUST be valid JSON. No extra text.
- Do not invent values. If missing, use null.
- Keep `evidence_excerpt` short and redact personal data not needed.
"""


def pdf_to_base64_images(pdf_path: Path, dpi: int = 200) -> list[str]:
    """Convert all pages of PDF to base64-encoded PNG images.

    Converts each page of the PDF to a PNG image that can be processed by 
    Ollama vision models.

    Args:
        pdf_path: Path to the PDF file.
        dpi: DPI resolution for rendering (default: 200).

    Returns:
        list[str]: List of base64-encoded PNG image data, one per page.

    Raises:
        ImportError: If pdf2image or PIL is not installed.
    """
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        import io
    except ImportError as e:
        raise ImportError(
            "pdf2image and Pillow are required for vision model extraction. "
            "Install with: pip install pdf2image Pillow"
        ) from e

    # Convert all pages of PDF to images
    images = convert_from_path(str(pdf_path), dpi=dpi)
    
    if not images:
        raise ValueError(f"Could not convert PDF to images: {pdf_path}")

    # Convert each PIL Image to base64 PNG
    base64_images = []
    for img in images:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        base64_images.append(base64.b64encode(img_bytes).decode("utf-8"))

    return base64_images


def call_ollama_for_iban_from_pdf(
    pdf_path: Path,
    model: str = None,
    ollama_url: str = None,
    timeout: int = 900,
) -> IbanExtractionResult:
    """Extract IBAN and BIC from all pages of PDF using Ollama vision model.

    Sends all pages of the PDF document to a locally hosted Ollama vision model 
    (e.g., qwen3-vl:30b) with a structured prompt designed for precise extraction 
    of banking identifiers.

    Args:
        pdf_path: Path to the PDF file.
        model: Ollama vision model name. If ``None``, uses ``OLLAMA_MODEL`` env var
            or defaults to ``"qwen3-vl:30b"``.
        ollama_url: Ollama API base URL. If ``None``, uses ``OLLAMA_URL`` env
            var or defaults to ``"http://localhost:11434"``.
        timeout: Request timeout in seconds (default: 300).

    Returns:
        IbanExtractionResult: Parsed extraction result with IBAN, BIC, and
        confidence information.

    Raises:
        requests.HTTPError: If the API request fails.
        ValueError: If the LLM response is not valid JSON.
    """
    if model is None:
        model = os.getenv("OLLAMA_MODEL", "qwen3-vl:30b")

    if ollama_url is None:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Convert all pages of PDF to base64 images for vision model
    pdf_base64_images = pdf_to_base64_images(pdf_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": LLM_SYSTEM_PROMPT + "\n\nExtract IBAN and BIC from this document:",
                "images": pdf_base64_images,  # Send all pages
            }
        ],
        "stream": False,
    }

    resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # Ollama returns: {"message": {"role": "...", "content": "..."}, ...}
    content = data.get("message", {}).get("content", "").strip()

    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON: {e}\nContent: {content}"
        ) from e

    return IbanExtractionResult(
        iban_raw=obj.get("iban_raw"),
        iban=obj.get("IBAN"),
        bic_raw=obj.get("BIC_raw"),
        bic=obj.get("BIC"),
        confidence=float(obj.get("confidence", 0.0)),
        evidence_excerpt=obj.get("evidence_excerpt"),
    )


# Keep the original text-based function for backwards compatibility
def call_ollama_for_iban(
    document_text: str,
    model: str = None,
    ollama_url: str = None,
    timeout: int = 300,
) -> IbanExtractionResult:
    """Extract IBAN and BIC from document text using Ollama LLM.

    This is the legacy text-based extraction. For PDF documents, use
    :func:`call_ollama_for_iban_from_pdf` instead.

    Args:
        document_text: Text extracted from the PDF document.
        model: Ollama model name. If ``None``, uses ``OLLAMA_MODEL`` env var
            or defaults to ``"gpt-oss:20b"``.
        ollama_url: Ollama API base URL. If ``None``, uses ``OLLAMA_URL`` env
            var or defaults to ``"http://localhost:11434"``.
        timeout: Request timeout in seconds (default: 300).

    Returns:
        IbanExtractionResult: Parsed extraction result with IBAN, BIC, and
        confidence information.

    Raises:
        requests.HTTPError: If the API request fails.
        ValueError: If the LLM response is not valid JSON.
    """
    if model is None:
        model = os.getenv("OLLAMA_MODEL", "qwen3-vl:30b")

    if ollama_url is None:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": document_text},
        ],
        "stream": False,
    }

    resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    content = data.get("message", {}).get("content", "").strip()

    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON: {e}\nContent: {content}"
        ) from e

    return IbanExtractionResult(
        iban_raw=obj.get("iban_raw"),
        iban=obj.get("IBAN"),
        bic_raw=obj.get("BIC_raw"),
        bic=obj.get("BIC"),
        confidence=float(obj.get("confidence", 0.0)),
        evidence_excerpt=obj.get("evidence_excerpt"),
    )
