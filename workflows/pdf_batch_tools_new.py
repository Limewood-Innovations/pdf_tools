#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF batch processing - split and clean PDFs.

This refactored script uses the modular tools from the `tools/` directory
to split PDFs into smaller parts and optionally remove blank pages.

Usage:
    python pdf_batch_tools.py --in-dir ./01_input --out-dir-split ./02_processed --out-dir-clean ./03_cleaned --every 2
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional

from convert import to_pdf14_untagged
from tools.split_pages import split_every_n_pages
from tools.blank_page import remove_blank_pages
from tools.move_to_archive import move_to_archive

logger = logging.getLogger("pdf_batch_tools")
logger.addHandler(logging.NullHandler())


def configure_logging(log_file: Optional[Path]) -> None:
    """Configure the module‑level logger.

    Args:
        log_file: Optional path to a log file.  When ``None`` only console
            logging is used.
    """
    from tools.configure_logging import StripColorFormatter

    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            StripColorFormatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(file_handler)


def ensure_pdf14(path: Path) -> None:
    """Convert the file at `path` to PDF 1.4 using the shared converter.

    Args:
        path: Path to the PDF file to convert.
    """
    import uuid

    temp_path = path.with_name(f"{path.stem}.__tmp_{uuid.uuid4().hex}{path.suffix}")
    try:
        to_pdf14_untagged(str(path), str(temp_path))
        temp_path.replace(path)
    except Exception:
        logger.exception("PDF 1.4 conversion failed for %s", path)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def process(
    in_dir: Path,
    out_dir_split: Path,
    out_dir_clean: Optional[Path],
    n: int = 2,
    clean: bool = True,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True,
    archive_dir: Optional[Path] = None,
    debug_pages: bool = False,
    fallback_on_all_blank: bool = True,
):
    """Process all PDFs in the input directory.

    The workflow is:
    1. Split each PDF into parts (if n > 0).
    2. Optionally remove blank pages from each part.
    3. Archive the original PDF.

    Args:
        in_dir: Directory containing input PDFs.
        out_dir_split: Directory for split PDFs.
        out_dir_clean: Optional directory for cleaned PDFs.
        n: Split every n pages (0 to disable splitting).
        clean: Whether to perform blank page removal.
        min_alnum_chars: Minimum alphanumeric characters for non-blank.
        min_alnum_ratio: Minimum alphanumeric ratio for non-blank.
        min_stream_bytes: Minimum content stream bytes for non-blank.
        treat_any_image_as_nonblank: Treat pages with images as non-blank.
        archive_dir: Optional archive directory for processed originals.
        debug_pages: Enable per-page debug output.
        fallback_on_all_blank: Keep original if all pages are blank.
    """
    pdfs: Iterable[Path] = sorted(
        [p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    )
    if not pdfs:
        logger.warning("Keine PDF in %s gefunden.", in_dir)
        return

    total_parts = 0
    total_cleaned = 0
    total_removed_pages = 0

    for idx, src in enumerate(pdfs, start=1):
        if n > 0:
            logger.info(
                "[%s/%s] Splitte %s alle %s Seiten → %s",
                idx,
                len(pdfs),
                src.name,
                n,
                out_dir_split,
            )
        else:
            logger.info(
                "[%s/%s] Kein Split (Parameter --every=%s) → kopiere %s nach %s",
                idx,
                len(pdfs),
                n,
                src.name,
                out_dir_split,
            )
        try:
            if n > 0:
                parts = split_every_n_pages(src, out_dir_split, n=n)
                # Ensure PDF 1.4 for each part
                for part in parts:
                    ensure_pdf14(part)
            else:
                out_dir_split.mkdir(parents=True, exist_ok=True)
                target = out_dir_split / src.name
                shutil.copy2(src, target)
                ensure_pdf14(target)
                parts = [target]

            total_parts += len(parts)
            logger.info("#" * 60)
            if n > 0:
                logger.info("Erzeugt: %s Teil-PDFs aus %s", len(parts), src.name)
            else:
                logger.info("Kopiert ohne Split: %s", parts[0].name)

            if clean and out_dir_clean is not None:
                logger.info(
                    "Entferne Leerseiten → %s (min_alnum=%s, min_alnum_ratio=%s, min_stream_bytes=%s)",
                    out_dir_clean,
                    min_alnum_chars,
                    min_alnum_ratio,
                    min_stream_bytes,
                )
                logger.info("-" * 60)
                for p in parts:
                    dst = out_dir_clean / p.name
                    try:
                        removed = remove_blank_pages(
                            p,
                            dst,
                            min_alnum_chars=min_alnum_chars,
                            min_alnum_ratio=min_alnum_ratio,
                            min_stream_bytes=min_stream_bytes,
                            treat_any_image_as_nonblank=treat_any_image_as_nonblank,
                            debug_pages=debug_pages,
                            fallback_on_all_blank=fallback_on_all_blank,
                        )
                        ensure_pdf14(dst)
                    except Exception:
                        logger.exception("Fehler bei Leerseiten-Entfernung für %s", p.name)
                        # Fallback: Original kopieren
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(p, dst)
                            removed = 0
                            ensure_pdf14(dst)
                        except Exception:
                            # Skip if copy also fails
                            continue
                    total_removed_pages += removed
                    total_cleaned += 1
                    logger.info("-" * 60)
        except Exception:
            logger.exception("Fehler beim Verarbeiten von %s", src.name)
        finally:
            # Move original to archive after processing attempt
            if archive_dir is not None and src.exists():
                moved_to = move_to_archive(src, archive_dir)
                logger.info("Archiviert: %s → %s", src.name, moved_to)

    logger.info("Gesamt erzeugte Teil-PDFs: %s", total_parts)
    if clean and out_dir_clean is not None:
        logger.info(
            "Gesamt bereinigte PDFs: %s, entfernte Leerseiten gesamt: %s",
            total_cleaned,
            total_removed_pages,
        )


def main():
    """CLI entry point for PDF batch processing."""
    ap = argparse.ArgumentParser(
        description="PDF-Stapel: splitte alle N Seiten und entferne optional Leerseiten (robust gegen OCR-Rauschen)."
    )
    ap.add_argument("--in-dir", required=True, help="Verzeichnis 1 (Quelle) mit der Eingangspdf")
    ap.add_argument("--out-dir-split", required=True, help="Verzeichnis 2 (Ausgabe der Teil-PDFs)")
    ap.add_argument("--out-dir-clean", help="Verzeichnis 3 (optional: bereinigte PDFs ohne Leerseiten)")
    ap.add_argument(
        "--every",
        type=int,
        default=0,
        help="Alle N Seiten splitten (nur bei N>0 aktiv, N<=0 deaktiviert Split; Standard: 0)",
    )
    ap.add_argument("--no-clean", action="store_true", help="keine Leerseiten-Entfernung durchführen")
    ap.add_argument(
        "--archive-dir", help="Optional: verarbeiteten Original-PDF nach Abschluss hierhin verschieben (Archiv)"
    )
    ap.add_argument("--log-file", help="Optional: Pfad zu einer Logdatei")

    ap.add_argument(
        "--min-alnum",
        type=int,
        default=5,
        help="Mindestanzahl an alphanumerischen Zeichen, damit Seite als 'nicht leer' gilt (Standard: 5)",
    )
    ap.add_argument(
        "--min-alnum-ratio",
        type=float,
        default=0.2,
        help="Mindestanteil alphanumerischer Zeichen (ohne Leerraum), damit Seite als 'nicht leer' gilt (Standard: 0.2)",
    )
    ap.add_argument(
        "--min-bytes",
        type=int,
        default=40,
        help="Mindestanzahl Bytes im Content-Stream, damit Seite als 'nicht leer' gilt (Standard: 40)",
    )
    ap.add_argument(
        "--image-nonblank", action="store_true", help="jede Bildseite als 'nicht leer' werten (Standard: an)"
    )
    ap.add_argument(
        "--no-image-nonblank",
        dest="image_nonblank",
        action="store_false",
        help="Bilder NICHT automatisch als 'nicht leer' werten",
    )
    ap.set_defaults(image_nonblank=True)
    ap.add_argument("--debug-pages", action="store_true", help="Pro Seite Debug-Infos und Entscheidungen ausgeben")
    ap.add_argument(
        "--no-fallback-empty",
        dest="fallback_on_all_blank",
        action="store_false",
        help="Kein Fallback: falls alle Seiten leer sind, keine Originalkopie schreiben (leere PDF)",
    )
    ap.set_defaults(fallback_on_all_blank=True)

    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir_split = Path(args.out_dir_split)
    out_dir_clean = Path(args.out_dir_clean) if args.out_dir_clean else None
    archive_dir = Path(args.archive_dir) if args.archive_dir else None
    log_file = Path(args.log_file).expanduser() if args.log_file else None
    clean = not args.no_clean and (out_dir_clean is not None)

    configure_logging(log_file)

    process(
        in_dir,
        out_dir_split,
        out_dir_clean,
        n=args.every,
        clean=clean,
        min_alnum_chars=args.min_alnum,
        min_alnum_ratio=args.min_alnum_ratio,
        min_stream_bytes=args.min_bytes,
        treat_any_image_as_nonblank=args.image_nonblank,
        archive_dir=archive_dir,
        debug_pages=args.debug_pages,
        fallback_on_all_blank=args.fallback_on_all_blank,
    )


if __name__ == "__main__":
    main()
