# -*- coding: utf-8 -*-
"""Normalization utilities for PDF files using Ghostscript.

This module provides the core functionality that was originally in
``pdf_normalizer.py``: locating the Ghostscript binary, normalising a PDF with a
chosen profile, and optionally archiving the original file.
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .find_ghostscript import find_ghostscript


def normalize_pdf(
    gs_bin: str,
    input_pdf: Path,
    output_pdf: Path,
    profile: str = "printer",
    compatibility: str = "1.4",
    logger: logging.Logger | None = None,
) -> None:
    """Normalize a single PDF via Ghostscript ``pdfwrite``.

    Args:
        gs_bin: Path to the Ghostscript executable.
        input_pdf: Source PDF to be processed.
        output_pdf: Destination path for the normalised PDF.
        profile: Ghostscript quality profile (e.g. ``"printer"``).
        compatibility: PDF compatibility level (default ``"1.4"``).
        logger: Optional logger; if omitted a temporary logger is created.
    """
    if logger is None:
        logger = logging.getLogger("pdf_normalizer")

    profile_map = {
        "screen": "/screen",
        "ebook": "/ebook",
        "printer": "/printer",
        "prepress": "/prepress",
        "default": "/default",
    }
    if profile not in profile_map:
        raise ValueError(f"Unknown profile '{profile}'. Use one of: {', '.join(profile_map)}")

    pdf_settings = profile_map[profile]
    cmd = [
        gs_bin,
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=pdfwrite",
        "-sColorConversionStrategy=LeaveColorUnchanged",
        f"-dCompatibilityLevel={compatibility}",
        f"-dPDFSETTINGS={pdf_settings}",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        f"-sOutputFile={str(output_pdf)}",
        str(input_pdf),
    ]
    logger.info("Normalizing: %s", input_pdf)
    subprocess.run(cmd, check=True)
    logger.info("Created: %s", output_pdf)


def archive_original(input_pdf: Path, archive_dir: Path, logger: logging.Logger | None = None) -> None:
    """Move *input_pdf* into *archive_dir*, handling name collisions.

    This mirrors the behaviour from the original script but is kept separate from the
    generic ``move_to_archive`` tool so that the normalizer can operate without a
    hard dependency on the batch‑processing utilities.
    """
    if logger is None:
        logger = logging.getLogger("pdf_normalizer")
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / input_pdf.name
    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = archive_dir / f"{input_pdf.stem}_{timestamp}{input_pdf.suffix}"
        logger.warning("Archive target already exists, using: %s", target.name)
    try:
        input_pdf.replace(target)
    except OSError:
        # Fallback for cross‑filesystem moves.
        shutil.copy2(input_pdf, target)
        input_pdf.unlink(missing_ok=True)
    logger.info("Archived original: %s -> %s", input_pdf.name, target)
