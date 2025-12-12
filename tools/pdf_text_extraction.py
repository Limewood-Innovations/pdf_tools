# -*- coding: utf-8 -*-
"""PDF text extraction utilities.

This module provides text extraction from PDF files using pdfplumber,
designed for extracting text from binary PDF data in memory.
"""

import io
from typing import List

import pdfplumber


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from a PDF given as bytes.

    This function uses pdfplumber to extract text from all pages of a PDF
    document provided as a byte array. It's particularly useful for processing
    PDFs that are received from APIs or stored in memory.

    Args:
        pdf_bytes: PDF file content as bytes.

    Returns:
        str: Extracted text from all pages, joined with newlines.
        Returns an empty string if no text could be extracted.

    Example:
        >>> with open("document.pdf", "rb") as f:
        ...     pdf_data = f.read()
        >>> text = extract_text_from_pdf_bytes(pdf_data)
        >>> print(text)
    """
    text_chunks: List[str] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

    return "\n".join(text_chunks).strip()


def extract_text_from_pdf_file(pdf_path: str) -> str:
    """Extract text from a PDF file on disk.

    Convenience wrapper around :func:`extract_text_from_pdf_bytes` for
    files on the filesystem.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        str: Extracted text from all pages.
    """
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return extract_text_from_pdf_bytes(pdf_bytes)
