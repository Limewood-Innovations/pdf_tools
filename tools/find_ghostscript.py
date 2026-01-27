# -*- coding: utf-8 -*-
"""Utility to locate the Ghostscript executable.

The original script defined ``GS_CANDIDATES`` and a ``find_ghostscript``
function.  This module isolates that logic so it can be imported by the
normalizer CLI and any other tool that needs Ghostscript.
"""

import shutil
from typing import List

# Common Ghostscript binary names on different platforms.
GS_CANDIDATES: List[str] = [
    "gswin64c.exe",  # Windows 64‑bit
    "gswin32c.exe",  # Windows 32‑bit
    "gs",            # Linux / macOS
]


def find_ghostscript() -> str:
    """Return the path to a Ghostscript executable.

    The function iterates over :data:`GS_CANDIDATES` and returns the first
    executable found on ``PATH``.  If none are found, a ``RuntimeError`` is raised.
    """
    for name in GS_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(
        "Ghostscript executable not found. Install Ghostscript and ensure 'gs' or 'gswin64c' is on PATH."
    )
