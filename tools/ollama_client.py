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


# Concise system prompt optimized for vision models
LLM_SYSTEM_PROMPT = """Extract IBAN and BIC from the document image.

Return ONLY valid JSON in this exact format:
{
  "iban_raw": "IBAN as shown in document",
  "IBAN": "AT771234567890123456",
  "BIC_raw": "BIC as shown",
  "BIC": "BKAUATWW",
  "confidence": 0.95,
  "evidence_excerpt": "short excerpt"
}

Rules:
- Extract payment-related IBAN (Austrian: AT + 2 digits + 16 digits)
- Extract BIC (8 or 11 uppercase characters)
- Normalize: remove spaces, uppercase
- Use null if not found
- Return ONLY JSON, no other text"""


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
                "content": LLM_SYSTEM_PROMPT,
                "images": pdf_base64_images,  # Send all pages
            }
        ],
        "stream": False,
        "format": "json",  # Force JSON output
        "options": {
            "temperature": 0.1,  # Lower temperature for more deterministic output
            "num_predict": 500,  # Allow up to 500 tokens for the response
        }
    }

    resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # Ollama returns: {"message": {"role": "...", "content": "..."}, ...}
    content = data.get("message", {}).get("content", "").strip()

    if not content:
        raise ValueError(
            f"LLM returned empty content. Full response: {json.dumps(data, indent=2)}"
        )

    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON: {e}\n"
            f"Content received: {content[:500]}...\n"
            f"Full response: {json.dumps(data, indent=2)}"
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

    if not content:
        raise ValueError(
            f"LLM returned empty content. Full response: {json.dumps(data, indent=2)}"
        )

    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON: {e}\n"
            f"Content received: {content[:500]}...\n"
            f"Full response: {json.dumps(data, indent=2)}"
        ) from e

    return IbanExtractionResult(
        iban_raw=obj.get("iban_raw"),
        iban=obj.get("IBAN"),
        bic_raw=obj.get("BIC_raw"),
        bic=obj.get("BIC"),
        confidence=float(obj.get("confidence", 0.0)),
        evidence_excerpt=obj.get("evidence_excerpt"),
    )

