# -*- coding: utf-8 -*-
"""Blank‑page detection and removal utilities.

This module provides :func:`is_blank_page` and :func:`remove_blank_pages`
extracted from the original ``pdf_batch_tools.py``.  The implementation relies
on shared helpers from :mod:`tools.utils`.
"""

import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter

from .utils import (
    _color_label,
    _resolve,
    _get_inherited,
    content_stream_bytes,
    count_alnum,
    page_has_images,
)

# Module‑level logger used for optional debug output.
_logger = logging.getLogger("pdf_batch_tools")

def is_blank_page(
    page,
    text_len_threshold: int = 1,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True,
    debug_pages: bool = False,
) -> bool:
    """Determine whether *page* should be considered blank.

    The heuristics match the original script: a page is non‑blank if it contains
    enough alphanumeric characters, a sufficient stream byte count, or an image
    (when ``treat_any_image_as_nonblank`` is ``True``).
    """
    try:
        txt = page.extract_text() or ""
    except Exception:
        txt = ""

    alnum_count = count_alnum(txt)
    non_ws_chars = sum(1 for c in txt if not c.isspace())
    alnum_ratio = (alnum_count / non_ws_chars) if non_ws_chars else 0.0
    stream_bytes = content_stream_bytes(page)

    if debug_pages:
        _logger.debug(
            "text_len=%s alnum=%s alnum_ratio=%.3f stream_bytes=%s",
            len(txt.strip()),
            alnum_count,
            alnum_ratio,
            stream_bytes,
        )
        if len(txt.strip()) <= 120 and txt.strip():
            _logger.debug("text_preview=%r", txt.strip())

    if alnum_count >= min_alnum_chars and alnum_ratio >= min_alnum_ratio:
        if debug_pages:
            _logger.debug("%s reason=alnum_threshold", _color_label("NON-BLANK"))
        return False

    if len(txt.strip()) >= text_len_threshold and alnum_count == 0:
        # No alnum but enough visible text – treat as non‑blank.
        pass

    if stream_bytes > min_stream_bytes:
        if debug_pages:
            _logger.debug(
                "%s reason=stream_bytes>%s",
                _color_label("NON-BLANK"),
                min_stream_bytes,
            )
        return False

    resources = _get_inherited(page, "/Resources")
    if treat_any_image_as_nonblank and page_has_images(resources):
        if debug_pages:
            _logger.debug("%s reason=image_found", _color_label("NON-BLANK"))
        return False

    if debug_pages:
        _logger.debug("%s reason=below_thresholds", _color_label("BLANK"))
    return True


def remove_blank_pages(
    src_pdf: Path,
    dst_pdf: Path,
    text_len_threshold: int = 1,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True,
    debug_pages: bool = False,
    fallback_on_all_blank: bool = True,
) -> int:
    """Copy *src_pdf* to *dst_pdf* while dropping blank pages.

    Returns the number of pages removed.
    """
    reader = PdfReader(str(src_pdf))
    writer = PdfWriter()
    removed = 0
    kept = 0
    for p in reader.pages:
        if is_blank_page(
            p,
            text_len_threshold=text_len_threshold,
            min_alnum_chars=min_alnum_chars,
            min_alnum_ratio=min_alnum_ratio,
            min_stream_bytes=min_stream_bytes,
            treat_any_image_as_nonblank=treat_any_image_as_nonblank,
            debug_pages=debug_pages,
        ):
            removed += 1
            continue
        writer.add_page(p)
        kept += 1

    if kept == 0:
        # Fallback handling – keep original or write empty PDF.
        if fallback_on_all_blank:
            dst_pdf.parent.mkdir(parents=True, exist_ok=True)
            # Copy original and ensure PDF‑1.4 header.
            import shutil
            shutil.copy2(src_pdf, dst_pdf)
        else:
            dst_pdf.parent.mkdir(parents=True, exist_ok=True)
            empty_writer = PdfWriter()
            with dst_pdf.open("wb") as f:
                empty_writer.write(f)
        return removed

    # Normal case – write cleaned PDF.
    from .utils import _strip_tags_from_writer

    _strip_tags_from_writer(writer)
    dst_pdf.parent.mkdir(parents=True, exist_ok=True)
    with dst_pdf.open("wb") as f:
        writer.write(f)
    return removed
