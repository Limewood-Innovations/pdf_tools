# -*- coding: utf-8 -*-
"""Utilities for splitting PDF files into parts.

This module provides :func:`split_every_n_pages` which splits a source PDF into
multiple PDFs each containing *n* pages.  It also contains a private helper
:func:`_create_pdf_writer` that creates a :class:`pypdf.PdfWriter` with the
required PDF‑1.4 header.

The implementation is extracted from ``pdf_batch_tools.py`` and has been
augmented with Google‑style docstrings.
"""

from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

# The original script used an ``IndirectObject`` fallback; we keep the import
# for compatibility but do not use it directly.
try:
    from pypdf.generic import IndirectObject  # type: ignore
except Exception:  # pragma: no cover
    IndirectObject = None  # type: ignore

from .utils import _strip_tags_from_writer


def _create_pdf_writer() -> PdfWriter:
    """Create a :class:`PdfWriter` configured for PDF‑1.4 output.

    Returns:
        PdfWriter: A writer instance with the ``%PDF-1.4`` header set when
        possible.
    """
    writer = PdfWriter()
    try:
        writer.pdf_header = "%PDF-1.4"
    except Exception:  # pragma: no cover – defensive, unlikely to fail
        pass
    return writer


def split_every_n_pages(src_pdf: Path, out_dir: Path, n: int = 2) -> List[Path]:
    """Split *src_pdf* into multiple PDFs each containing *n* pages.

    Args:
        src_pdf: Path to the source PDF.
        out_dir: Directory where the split parts will be written.
        n: Number of pages per part.  Must be greater than ``0``.

    Returns:
        List[Path]: Paths to the newly created part PDFs.

    Raises:
        ValueError: If *n* is not a positive integer.
    """
    if n <= 0:
        raise ValueError("split_every_n_pages requires n > 0")

    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(src_pdf))
    total_pages = len(reader.pages)
    parts: List[Path] = []
    idx = 0
    part_no = 1
    while idx < total_pages:
        writer = _create_pdf_writer()
        for offset in range(n):
            if idx + offset < total_pages:
                writer.add_page(reader.pages[idx + offset])
        _strip_tags_from_writer(writer)
        out_path = out_dir / f"{src_pdf.stem}_part_{part_no:03d}.pdf"
        with out_path.open("wb") as f:
            writer.write(f)
        parts.append(out_path)
        part_no += 1
        idx += n
    return parts
