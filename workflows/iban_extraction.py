#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IBAN extraction from Darlehen PDFs using modular tools.

This refactored script uses the modular tools from the `tools/` directory
to extract IBAN and BIC information from loan documents.

Usage:
    python iban_extraction.py --input-dir ./01_input --log-file ./logs/iban.log
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import shutil

# Add the project root to sys.path to enable importing from tools
# This ensures the script works when run from any directory
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.split_pages import split_every_n_pages
from tools.ollama_client import call_ollama_for_iban_from_pdf
from tools.iban_validator import validate_austrian_iban, extract_account_info
from tools.pushover_client import send_pushover_message
from tools.setup_logging import setup_logging

# Module-level logger (will be configured in main())
logger = None


def process_single_file(pdf_path: Path, output_dir: Path, error_dir: Path, enable_pushover: bool = True) -> bool:
    """Process a single PDF file to extract IBAN information.

    This function implements the complete workflow:
    1. Call Ollama vision model for IBAN/BIC extraction directly from PDF
    2. Validate Austrian IBAN format
    3. Derive bank code and account number
    4. Move processed file to output directory (or error directory on failure)
    5. Send Pushover notification (if enabled)

    Args:
        pdf_path: Path to the PDF file to process.
        output_dir: Directory to move successfully processed files to.
        error_dir: Directory to move failed files to.
        enable_pushover: Whether to send Pushover notifications (default: True).

    Returns:
        bool: ``True`` if processing succeeded, ``False`` on error.
    """
    logger.info(f"Processing file: {pdf_path.name}")

    # Step 1: Call Ollama vision model for IBAN/BIC extraction
    try:
        extraction = call_ollama_for_iban_from_pdf(pdf_path)
    except Exception as e:
        logger.error(f"Ollama vision model call failed: {e}")
        if enable_pushover:
            send_pushover_message("ERROR", title="IBAN Extraction")
        # Move to error directory
        error_dir.mkdir(parents=True, exist_ok=True)
        error_path = error_dir / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(error_path))
            logger.info(f"Moved to error directory: {error_path}")
        except Exception as move_err:
            logger.warning(f"Could not move to error directory: {move_err}")
        return False

    if not extraction.iban:
        logger.warning("No IBAN found by Ollama; sending ERROR notification")
        if enable_pushover:
            send_pushover_message("ERROR", title="IBAN Extraction")
        # Move to error directory
        error_dir.mkdir(parents=True, exist_ok=True)
        error_path = error_dir / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(error_path))
            logger.info(f"Moved to error directory: {error_path}")
        except Exception as move_err:
            logger.warning(f"Could not move to error directory: {move_err}")
        return False

    # Step 2: Validate Austrian IBAN and derive bank code / account number
    iban = extraction.iban
    if not validate_austrian_iban(iban):
        logger.error(f"Invalid Austrian IBAN extracted: {iban}")
        if enable_pushover:
            send_pushover_message("ERROR", title="IBAN Extraction")
        # Move to error directory
        error_dir.mkdir(parents=True, exist_ok=True)
        error_path = error_dir / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(error_path))
            logger.info(f"Moved to error directory: {error_path}")
        except Exception as move_err:
            logger.warning(f"Could not move to error directory: {move_err}")
        return False

    try:
        account_info = extract_account_info(iban)
    except Exception as e:
        logger.error(f"Failed to derive bankCode/accountNumber: {e}")
        if enable_pushover:
            send_pushover_message("ERROR", title="IBAN Extraction")
        # Move to error directory
        error_dir.mkdir(parents=True, exist_ok=True)
        error_path = error_dir / pdf_path.name
        try:
            shutil.move(str(pdf_path), str(error_path))
            logger.info(f"Moved to error directory: {error_path}")
        except Exception as move_err:
            logger.warning(f"Could not move to error directory: {move_err}")
        return False

    # Step 3: Move processed file to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{account_info.account_number}.pdf"
    
    try:
        shutil.move(str(pdf_path), str(output_path))
        logger.info(f"Moved to: {output_path}")
    except Exception as e:
        logger.warning(f"Failed to move file: {e}")
        # Continue anyway, we still got the IBAN

    # Step 4: Send pushover message with IBAN
    logger.info(f"✓ Extracted IBAN: {account_info.iban}")
    logger.info(f"  Bank code: {account_info.bank_code}")
    logger.info(f"  Account number: {account_info.account_number}")
    logger.info(f"  Confidence: {extraction.confidence:.2f}")

    if enable_pushover:
        send_pushover_message(
            f"IBAN: {account_info.iban}\nAccount: {account_info.account_number}",
            title="IBAN Extracted",
        )

    return True


def process_pdf_directory(
    input_dir: str,
    output_dir: str = "./02_processed",
    error_dir: str = "./98_error",
    archive_dir: str = "./99_archived",
    enable_pushover: bool = True,
) -> int:
    """Process all PDFs in an input directory through the complete workflow.

    Workflow steps (for each PDF):
    1. Split PDF into 2-page chunks using local tool
    2. For each chunk, extract IBAN using Ollama vision model
    3. Move processed files to output directory (or error directory on failure)
    4. Archive original PDF to archive directory after successful processing

    Args:
        input_dir: Directory containing input PDF files.
        output_dir: Directory to move processed files to (default: ./02_processed).
        error_dir: Directory to move failed files to (default: ./98_error).
        archive_dir: Directory to archive original PDFs to (default: ./99_archived).
        enable_pushover: Whether to send Pushover notifications (default: True).

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    input_path = Path(input_dir)
    
    if not input_path.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # Find all PDF files in input directory
    pdf_files = sorted(input_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0
    
    logger.info(f"Found {len(pdf_files)} PDF(s) in {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Error directory: {error_dir}")
    logger.info("=" * 60)
    
    total_success = 0
    total_errors = 0
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
        logger.info("-" * 60)
        
        temp_dir = pdf_file.parent / f".{pdf_file.stem}_parts"
        
        # Step 1: Split PDF into parts using local tool
        try:
            temp_dir.mkdir(exist_ok=True)
            split_parts = split_every_n_pages(pdf_file, temp_dir, n=2)
            logger.info(f"Split into {len(split_parts)} parts")
        except Exception as e:
            logger.error(f"PDF splitting failed: {e}")
            if enable_pushover:
                send_pushover_message("ERROR", title="IBAN Extraction")
            # Move original file to error directory
            error_path = Path(error_dir)
            error_path.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(pdf_file), str(error_path / pdf_file.name))
                logger.info(f"Moved to error directory: {error_path / pdf_file.name}")
            except Exception:
                pass
            total_errors += 1
            continue

        if not split_parts:
            logger.error("No parts created from splitting")
            if enable_pushover:
                send_pushover_message("ERROR", title="IBAN Extraction")
            total_errors += 1
            continue

        # Step 2: Process each split part
        success_count = 0
        error_count = 0
        output_path = Path(output_dir)
        error_path = Path(error_dir)
        
        try:
            for part_path in split_parts:
                if process_single_file(part_path, output_path, error_path, enable_pushover):
                    success_count += 1
                else:
                    error_count += 1
        finally:
            # Cleanup temporary directory (files were moved to output_dir or error_dir)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        logger.info(f"Parts processed: {success_count} success, {error_count} errors")
        total_success += success_count
        total_errors += error_count

        # Archive original PDF if any parts were successfully processed
        if success_count > 0:
            archive_path = Path(archive_dir)
            archive_path.mkdir(parents=True, exist_ok=True)
            archive_file = archive_path / pdf_file.name
            try:
                shutil.move(str(pdf_file), str(archive_file))
                logger.info(f"Archived original to: {archive_file}")
            except Exception as e:
                logger.warning(f"Failed to archive original file: {e}")

    logger.info("\n" + "=" * 60)
    logger.info(f"[SUMMARY] Total parts processed: {total_success} success, {total_errors} errors")
    if total_errors > 0:
        logger.info(f"[SUMMARY] Error files location: {error_dir}")
    if total_success > 0:
        logger.info(f"[SUMMARY] Success files location: {output_dir}")
    
    return 0 if total_success > 0 else 1


def process_pdf(pdf_path: str, output_dir: str = "./02_processed", error_dir: str = "./98_error") -> int:
    """Process a single PDF file (legacy function, use process_pdf_directory instead).

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory to move processed files to (default: ./02_processed).
        error_dir: Directory to move failed files to (default: ./98_error).

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    print(f"[INFO] Processing original PDF: {pdf_path}")
    
    pdf_file = Path(pdf_path)
    temp_dir = pdf_file.parent / f".{pdf_file.stem}_parts"
    
    # Step 1: Split PDF into parts using local tool
    try:
        temp_dir.mkdir(exist_ok=True)
        split_parts = split_every_n_pages(pdf_file, temp_dir, n=2)
        print(f"[INFO] Split into {len(split_parts)} parts")
    except Exception as e:
        print(f"[ERROR] PDF splitting failed: {e}", file=sys.stderr)
        send_pushover_message("ERROR", title="IBAN Extraction")
        return 1

    if not split_parts:
        print("[ERROR] No parts created from splitting", file=sys.stderr)
        send_pushover_message("ERROR", title="IBAN Extraction")
        return 1

    # Step 2: Process each split part
    success_count = 0
    error_count = 0
    output_path = Path(output_dir)
    error_path = Path(error_dir)
    
    try:
        for part_path in split_parts:
            if process_single_file(part_path, output_path, error_path):
                success_count += 1
            else:
                error_count += 1
    finally:
        # Cleanup temporary directory (files were moved to output_dir or error_dir)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"[INFO] Cleaned up temporary directory {temp_dir}")

    print(f"\n[INFO] Processed {success_count}/{len(split_parts)} files successfully")
    if error_count > 0:
        print(f"[INFO] {error_count} files moved to error directory: {error_dir}")

    return 0 if success_count > 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for IBAN extraction.

    Args:
        argv: Command-line arguments (for testing). If ``None``, uses sys.argv.

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        description="Extract IBAN/BIC from NHG Darlehen PDFs using Ollama vision model."
    )
    parser.add_argument(
        "--input-dir",
        default="./01_input",
        help="Directory containing input PDF files (default: ./01_input)"
    )
    parser.add_argument(
        "--output-dir",
        default="./02_processed",
        help="Directory to move processed files to (default: ./02_processed)"
    )
    parser.add_argument(
        "--error-dir",
        default="./98_error",
        help="Directory to move failed files to (default: ./98_error)"
    )
    parser.add_argument(
        "--archive-dir",
        default="./99_archived",
        help="Directory to archive original PDFs to (default: ./99_archived)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (optional). If not set, logs only to console."
    )
    parser.add_argument(
        "--no-pushover",
        action="store_true",
        help="Disable Pushover notifications"
    )

    args = parser.parse_args(argv)

    # Configure logging and set global logger
    global logger
    logger = setup_logging(
        log_file=args.log_file,
        console=True,
    )

    return process_pdf_directory(
        args.input_dir,
        args.output_dir,
        args.error_dir,
        args.archive_dir,
        enable_pushover=not args.no_pushover
    )


if __name__ == "__main__":
    raise SystemExit(main())
