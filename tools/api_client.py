# -*- coding: utf-8 -*-
"""API client for PDF split service.

This module provides functions to interact with the PDF split API service,
which splits PDFs and returns them as a ZIP file. It also handles separation
of watermark pages from content pages.
"""

import io
import os
import zipfile
from typing import List, Tuple

import requests


def call_split_api(
    pdf_path: str,
    api_url: str = None,
    n: int = 2,
    timeout: int = 300
) -> List[Tuple[str, bytes]]:
    """Send a PDF to the split API and return extracted files.

    The split API endpoint receives a PDF file, splits it into parts,
    and returns a ZIP archive containing the split files.

    Args:
        pdf_path: Path to the input PDF file.
        api_url: URL of the split API endpoint. If ``None``, uses the
            ``NHG_SPLIT_API_URL`` environment variable or default.
        n: Number of pages per split (default: 2).
        timeout: Request timeout in seconds (default: 300).

    Returns:
        List[Tuple[str, bytes]]: List of (filename, content) tuples for each
        file extracted from the ZIP response.

    Raises:
        requests.HTTPError: If the API request fails.
        ValueError: If the response is not a ZIP file.
    """
    if api_url is None:
        api_url = os.getenv(
            "NHG_SPLIT_API_URL",
            f"http://ai.limewood.at:8000/split?n={n}"
        )

    with open(pdf_path, "rb") as f:
        files = {"upload": (os.path.basename(pdf_path), f, "application/pdf")}
        response = requests.post(api_url, files=files, timeout=timeout)

    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")

    if "zip" not in content_type.lower():
        raise ValueError(
            f"Expected ZIP from split API, got Content-Type: {content_type}"
        )

    zip_bytes = io.BytesIO(response.content)
    extracted_files: List[Tuple[str, bytes]] = []

    with zipfile.ZipFile(zip_bytes, "r") as zf:
        for name in zf.namelist():
            with zf.open(name) as file:
                extracted_files.append((name, file.read()))

    return extracted_files


def separate_watermark_and_image_files(
    files: List[Tuple[str, bytes]]
) -> List[Tuple[str, bytes]]:
    """Separate watermark pages from content pages.

    Filters the list of files to return only non-watermark pages.
    Files are classified as watermark if their filename contains
    the word "watermark" (case-insensitive).

    Args:
        files: List of (filename, content) tuples.

    Returns:
        List[Tuple[str, bytes]]: Filtered list containing only non-watermark
        pages (classified as "Image" type).
    """
    image_files: List[Tuple[str, bytes]] = []

    for file_name, data in files:
        lower_name = file_name.lower()
        # Classify as Watermark if filename contains "watermark"
        if "watermark" not in lower_name:
            image_files.append((file_name, data))

    return image_files
