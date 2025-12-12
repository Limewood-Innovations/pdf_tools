# -*- coding: utf-8 -*-
"""Utility to move processed PDFs to an archive directory.

The function mirrors the original ``move_to_archive`` helper from
``pdf_batch_tools.py`` but is placed in its own module so it can be reused by
both the batch‑processing workflow and the normalizer workflow.
"""

from pathlib import Path
from datetime import datetime
import shutil


def move_to_archive(src: Path, archive_dir: Path) -> Path:
    """Move *src* into *archive_dir*, handling name collisions.

    If a file with the same name already exists in the archive, a timestamp is
    appended to the filename to avoid overwriting.

    Args:
        src: Path to the source PDF that should be archived.
        archive_dir: Destination directory for archived PDFs.

    Returns:
        Path: The final path of the archived file.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / src.name
    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = archive_dir / f"{src.stem}_{timestamp}{src.suffix}"
    try:
        src.replace(target)
    except OSError:
        # Fallback for cross‑filesystem moves.
        shutil.copy2(src, target)
        src.unlink(missing_ok=True)
    return target
