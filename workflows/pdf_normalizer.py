#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF Normalizer - normalize PDFs using Ghostscript.

This refactored script uses the modular tools from the `tools/` directory
to normalize PDFs with Ghostscript and optionally archive the originals.

Usage:
    python pdf_normalizer.py input_dir output_dir --profile printer --archive-dir ./99_archived
"""

import argparse
import subprocess
from pathlib import Path
import sys

# Add the project root to sys.path to enable importing from tools
# This ensures the script works when run from any directory
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.setup_logging import setup_logging
from tools.find_ghostscript import find_ghostscript
from tools.normalize import normalize_pdf, archive_original
from tools.convert_to_pdfa import convert_to_pdfa


def main() -> None:
    """CLI entry point for PDF normalization."""
    parser = argparse.ArgumentParser(description="Normalize all PDFs in a directory using Ghostscript.")
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
        "--pdfa",
        action="store_true",
        help="If set, convert the normalized PDF to PDF/A-1b after processing.",
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
        console=True,
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
            # Optionally convert to PDF/A
            if args.pdfa:
                pdfa_path = convert_to_pdfa(output_pdf, output_pdf.with_suffix('.pdfa.pdf'))
                logger.info("Converted to PDF/A: %s", pdfa_path)


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
