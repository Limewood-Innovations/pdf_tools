# -*- coding: utf-8 -*-
"""Normalization utilities for PDF files using Ghostscript.

This module provides the core functionality that was originally in
``pdf_normalizer.py``: locating the Ghostscript binary, normalising a PDF with a
chosen profile, and optionally archiving the original file.
"""

import logging
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pikepdf

from .find_ghostscript import find_ghostscript


def _repair_pdf(input_pdf: Path, logger: logging.Logger) -> Path | None:
    """Re-save *input_pdf* through pikepdf to fix broken object references.

    Returns the path to a repaired temp file, or ``None`` if the PDF opens
    cleanly and no repair is needed.
    """
    try:
        with pikepdf.open(input_pdf) as pdf:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix="repair_", delete=False
            )
            tmp.close()
            pdf.save(tmp.name)
            logger.info("Pre-repaired via pikepdf: %s", input_pdf.name)
            return Path(tmp.name)
    except Exception as exc:
        logger.warning("pikepdf repair failed for %s: %s", input_pdf.name, exc)
        return None


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

    # Ghostscript interprets % in output filenames as printf format specifiers.
    # Escape them so literal % characters pass through.
    safe_output = str(output_pdf).replace("%", "%%")

    pdf_settings = profile_map[profile]

    # Pre-repair the input through pikepdf to fix broken object references
    # that would cause GS to hang or produce stub output.
    repaired = _repair_pdf(input_pdf, logger)
    gs_input = str(repaired) if repaired else str(input_pdf)

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
        f"-sOutputFile={safe_output}",
        gs_input,
    ]
    logger.info("Normalizing: %s", input_pdf)
    input_size = input_pdf.stat().st_size
    try:
        subprocess.run(cmd, check=True, timeout=300)
    except subprocess.TimeoutExpired:
        logger.error(
            "Ghostscript timed out after 300s for %s — skipping file", input_pdf
        )
        output_pdf.unlink(missing_ok=True)
        raise subprocess.CalledProcessError(1, cmd)
    finally:
        if repaired:
            repaired.unlink(missing_ok=True)

    # Validate output: GS can silently produce a ~6 KB stub for problematic inputs
    if not output_pdf.exists():
        raise subprocess.CalledProcessError(1, cmd)
    output_size = output_pdf.stat().st_size
    min_size = min(8192, input_size // 4)
    if output_size < min_size:
        logger.error(
            "Ghostscript produced suspicious output for %s: %d bytes (input was %d bytes) — removing",
            input_pdf, output_size, input_size,
        )
        output_pdf.unlink(missing_ok=True)
        raise subprocess.CalledProcessError(1, cmd)

    logger.info("Created: %s (%d bytes)", output_pdf, output_size)


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
