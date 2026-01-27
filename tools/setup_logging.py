# -*- coding: utf-8 -*-
"""Logging configuration for the PDF normalizer.

This mirrors the ``setup_logging`` function from the original ``pdf_normalizer``
script but is placed in its own module so it can be reused by the CLI and any
future automation.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    console: bool = True,
) -> logging.Logger:
    """Create and configure a logger for the normalizer.

    Args:
        log_file: Optional path to a rotating log file.  If ``None`` only console
            logging is configured.
        max_bytes: Maximum size of a log file before rotation (default 5 MiB).
        backup_count: Number of rotated log files to retain.
        console: Whether to add a ``StreamHandler`` for stdout.

    Returns:
        logging.Logger: Configured logger named ``"pdf_normalizer"``.
    """
    logger = logging.getLogger("pdf_normalizer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
