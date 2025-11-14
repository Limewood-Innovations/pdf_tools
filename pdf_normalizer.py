#!/usr/bin/env python3
"""
normalize_pdf_with_ghostscript.py

Normalizes ALL PDFs in a source directory using Ghostscript
and writes the results into a target directory.

Features:
- Auto-archive original PDFs after successful processing
- Delete processed files from input directory (by moving them to archive)
- Log with rotation via RotatingFileHandler

Usage:
    python normalize_pdf_with_ghostscript.py input_dir output_dir
    python normalize_pdf_with_ghostscript.py input_dir output_dir --profile printer
    python normalize_pdf_with_ghostscript.py input_dir output_dir \
        --archive-dir ./99_archived/originals/NH/ \
        --log-file ./logs/pdf_nh.log
"""

import argparse
import subprocess
import shutil
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Common Ghostscript binary names on different platforms
GS_CANDIDATES = [
    "gswin64c.exe",  # Windows 64-bit
    "gswin32c.exe",  # Windows 32-bit
    "gs"             # Linux/macOS
]


def find_ghostscript() -> str:
    """Find Ghostscript executable on PATH."""
    for name in GS_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(
        "Ghostscript executable not found. "
        "Install Ghostscript 10.06.0 and ensure 'gs' or 'gswin64c' is on PATH."
    )


def setup_logging(
    log_file: Path | None,
    max_bytes: int,
    backup_count: int,
    console: bool = True,
) -> logging.Logger:
    """Configure logging with optional file rotation and console output."""
    logger = logging.getLogger("pdf_normalizer")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if main() would ever be called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def normalize_pdf(
    gs_bin: str,
    input_pdf: Path,
    output_pdf: Path,
    profile: str,
    compatibility: str,
    logger: logging.Logger,
) -> None:
    """Normalize a single PDF via Ghostscript pdfwrite."""
    profile_map = {
        "screen": "/screen",
        "ebook": "/ebook",
        "printer": "/printer",
        "prepress": "/prepress",
        "default": "/default",
    }

    if profile not in profile_map:
        raise ValueError(
            f"Unknown profile '{profile}'. "
            f"Use one of: {', '.join(profile_map.keys())}"
        )

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


def archive_original(
    input_pdf: Path,
    archive_dir: Path,
    logger: logging.Logger,
) -> None:
    """Move the original PDF to the archive directory.

    If a file with the same name already exists in the archive,
    append a timestamp to avoid overwriting.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / input_pdf.name

    if target.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = archive_dir / f"{input_pdf.stem}_{timestamp}{input_pdf.suffix}"
        logger.warning(
            "Archive target already exists, using: %s", target.name
        )

    input_pdf.rename(target)
    logger.info("Archived original: %s -> %s", input_pdf.name, target)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize all PDFs in a directory using Ghostscript."
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing PDF files.")
    parser.add_argument("output_dir", type=Path, help="Directory for normalized PDFs.")
    parser.add_argument(
        "--profile",
        choices=["screen", "ebook", "printer", "prepress", "default"],
        default="printer",
        help="Ghostscript quality profile (default: printer)",
    )
    parser.add_argument(
        "--compat",
        default="1.4",
        help="PDF compatibility level (default: 1.4).",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help=(
            "Directory to move original PDFs to after successful processing. "
            "If not set, originals stay in the input directory."
        ),
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file. If set, logs will rotate based on size.",
    )
    parser.add_argument(
        "--log-max-bytes",
        type=int,
        default=5 * 1024 * 1024,  # 5 MB
        help="Maximum log file size in bytes before rotation (default: 5MB).",
    )
    parser.add_argument(
        "--log-backup-count",
        type=int,
        default=5,
        help="Number of rotated log files to keep (default: 5).",
    )

    args = parser.parse_args()

    logger = setup_logging(
        log_file=args.log_file,
        max_bytes=args.log_max_bytes,
        backup_count=args.log_backup_count,
        console=True,  # cron output is still helpful for quick debugging
    )

    if not args.input_dir.is_dir():
        logger.error("Input directory not found: %s", args.input_dir)
        raise SystemExit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        gs_bin = find_ghostscript()
    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1)

    pdf_files = sorted(args.input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("No PDF files found in input directory: %s", args.input_dir)
        return

    logger.info(
        "Found %d PDF(s) in %s. Output dir: %s",
        len(pdf_files),
        args.input_dir,
        args.output_dir,
    )

    for pdf in pdf_files:
        output_pdf = args.output_dir / pdf.name
        try:
            normalize_pdf(
                gs_bin=gs_bin,
                input_pdf=pdf,
                output_pdf=output_pdf,
                profile=args.profile,
                compatibility=args.compat,
                logger=logger,
            )

            # Auto-archive & delete from input
            if args.archive_dir is not None:
                archive_original(pdf, args.archive_dir, logger)
            else:
                # If no archive-dir specified, we keep original in place.
                logger.info("No archive directory configured, keeping original: %s", pdf)

        except subprocess.CalledProcessError as e:
            logger.error(
                "Ghostscript failed for %s with return code %s",
                pdf,
                e.returncode,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected error while processing %s: %s", pdf, e)

    logger.info("All PDFs processed.")


if __name__ == "__main__":
    main()