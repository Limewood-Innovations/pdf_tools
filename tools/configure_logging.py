# -*- coding: utf-8 -*-
"""Logging configuration utilities for PDF batch processing.

This module provides a logger setup function, a custom formatter that strips ANSI
color codes, and a helper to colour‑label log messages.  The implementation is
based on the original `pdf_batch_tools.py` script.
"""

import logging
import re
from logging import Formatter
from typing import Optional

# Regular expression to strip ANSI escape sequences.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class StripColorFormatter(Formatter):
    """Formatter that removes ANSI colour codes from log messages.

    The original script used this formatter to keep log files free of terminal
    colour escape sequences while preserving colour output on the console.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return _ANSI_ESCAPE_RE.sub("", message)


def _color_label(label: str) -> str:
    """Return a colour‑coded label for console output.

    Args:
        label: The label text, e.g. ``"BLANK"`` or ``"NON-BLANK"``.

    Returns:
        The label wrapped in ANSI colour codes if it matches a known value,
        otherwise the original label.
    """
    if label == "BLANK":
        return f"\033[31m{label}\033[0m"  # Red
    if label == "NON-BLANK":
        return f"\033[32m{label}\033[0m"  # Green
    return label


def configure_logging(log_file: Optional[Path] = None) -> None:
    """Configure the module‑level logger.

    The logger is named ``"pdf_batch_tools"`` and is configured to emit DEBUG
    level messages.  If *log_file* is supplied a rotating file handler is added;
    otherwise only console output is configured.

    Args:
        log_file: Optional path to a log file.  When ``None`` only console
            logging is used.
    """
    logger = logging.getLogger("pdf_batch_tools")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StripColorFormatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(file_handler)
