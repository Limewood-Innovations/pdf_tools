#!/usr/bin/env python3
import argparse
import logging
import re
import sys
from pathlib import Path
import shutil
from typing import Iterable, Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject
try:
    from pypdf.generic import IndirectObject  # type: ignore
except Exception:  # compatibility if symbol not exported
    IndirectObject = None  # type: ignore

ALNUM_RE = re.compile(r"[0-9A-Za-zÄÖÜäöüß]")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_RESET = "\033[0m"


logger = logging.getLogger("pdf_batch_tools")
logger.addHandler(logging.NullHandler())


class StripColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return ANSI_ESCAPE_RE.sub("", message)


def _color_label(label: str) -> str:
    if label == "BLANK":
        return f"{COLOR_RED}{label}{COLOR_RESET}"
    if label == "NON-BLANK":
        return f"{COLOR_GREEN}{label}{COLOR_RESET}"
    return label


def configure_logging(log_file: Optional[Path]) -> None:
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
        file_handler.setFormatter(StripColorFormatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(file_handler)

def split_every_n_pages(src_pdf: Path, out_dir: Path, n: int = 2) -> list[Path]:
    if n <= 0:
        raise ValueError("split_every_n_pages requires n > 0")
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(src_pdf))
    total = len(reader.pages)
    parts: list[Path] = []
    idx = 0
    part_no = 1
    while idx < total:
        writer = PdfWriter()
        for j in range(n):
            if idx + j < total:
                writer.add_page(reader.pages[idx + j])
        _strip_tags_from_writer(writer)
        out_path = out_dir / f"{src_pdf.stem}_part_{part_no:03d}.pdf"
        with out_path.open("wb") as f:
            writer.write(f)
        parts.append(out_path)
        part_no += 1
        idx += n
    return parts

def _resolve(obj, max_hops: int = 5):
    """Resolve indirect objects safely with a hop limit.

    Some objects may return themselves for get_object(); guard against loops.
    """
    try:
        for _ in range(max_hops):
            if hasattr(obj, "get_object"):
                nxt = obj.get_object()
                if nxt is obj or nxt is None:
                    break
                obj = nxt
            else:
                break
    except Exception:
        return obj
    return obj

def _get_inherited(page_like, name: str):
    """Resolve a key (e.g., '/Resources') on a page, walking up the /Parent chain.

    Works with pypdf PageObject (dict-like) and raw dictionaries.
    """
    name_key = NameObject(name)
    cur = _resolve(page_like)
    hops = 0
    while cur is not None and hops < 10:
        try:
            if isinstance(cur, dict):
                if name_key in cur:
                    return _resolve(cur.get(name_key))
                cur = _resolve(cur.get(NameObject("/Parent")))
            else:
                # PageObject is mapping-like
                try:
                    val = cur.get(name_key)
                except Exception:
                    val = None
                if val is not None:
                    return _resolve(val)
                try:
                    cur = _resolve(cur.get(NameObject("/Parent")))
                except Exception:
                    cur = None
        except Exception:
            break
        hops += 1
    return None

def page_has_images(resources: Optional[DictionaryObject]) -> bool:
    if not resources:
        return False
    try:
        res = _resolve(resources)
        xobjs = _resolve(res.get(NameObject("/XObject"))) if isinstance(res, dict) else None
        if not isinstance(xobjs, dict):
            return False
        for _, x in list(xobjs.items()):
            x = _resolve(x)
            if not isinstance(x, dict):
                # Try to access as stream/dict-like
                try:
                    subtype = x.get(NameObject("/Subtype"))
                except Exception:
                    continue
            else:
                subtype = x.get(NameObject("/Subtype"))
            try:
                subval = subtype if isinstance(subtype, str) else (subtype and str(subtype))
            except Exception:
                subval = None
            if subval == "/Image":
                return True
            if subval == "/Form":
                # nested resources
                nested = _resolve(x.get(NameObject("/Resources"))) if isinstance(x, dict) else None
                if page_has_images(nested):
                    return True
    except Exception:
        # Be conservative: if we fail to inspect, do not treat as blank
        return True
    return False

def content_stream_bytes(page) -> int:
    try:
        contents = page.get_contents()
        if contents is None:
            return 0
        if isinstance(contents, list):
            return sum(len(obj.get_data()) for obj in contents if hasattr(obj, "get_data"))
        return len(contents.get_data()) if hasattr(contents, "get_data") else 0
    except Exception:
        return 0

def count_alnum(text: str) -> int:
    return len(ALNUM_RE.findall(text))

def is_blank_page(
    page,
    text_len_threshold: int = 1,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True,
    debug_pages: bool = False,
) -> bool:
    try:
        txt = page.extract_text() or ""
    except Exception:
        txt = ""

    alnum_count = count_alnum(txt)
    non_ws_chars = sum(1 for c in txt if not c.isspace())
    alnum_ratio = (alnum_count / non_ws_chars) if non_ws_chars else 0.0
    stream_bytes = content_stream_bytes(page)
    if debug_pages:
        logger.debug(
            "text_len=%s alnum=%s alnum_ratio=%.3f stream_bytes=%s",
            len(txt.strip()),
            alnum_count,
            alnum_ratio,
            stream_bytes,
        )
        if len(txt.strip()) <= 120 and txt.strip():
            logger.debug("text_preview=%r", txt.strip())
    if alnum_count >= min_alnum_chars and alnum_ratio >= min_alnum_ratio:
        if debug_pages:
            logger.debug("%s reason=alnum_threshold", _color_label("NON-BLANK"))
        return False

    if len(txt.strip()) >= text_len_threshold and alnum_count == 0:
        pass

    if stream_bytes > min_stream_bytes:
        if debug_pages:
            logger.debug(
                "%s reason=stream_bytes>%s",
                _color_label("NON-BLANK"),
                min_stream_bytes,
            )
        return False

    # Resolve resources with inheritance from Parent nodes (only if needed)
    resources = _get_inherited(page, "/Resources")
    if treat_any_image_as_nonblank and page_has_images(resources):
        if debug_pages:
            logger.debug("%s reason=image_found", _color_label("NON-BLANK"))
        return False

    if debug_pages:
        logger.debug("%s reason=below_thresholds", _color_label("BLANK"))
    return True

def remove_blank_pages(
    src_pdf: Path,
    dst_pdf: Path,
    text_len_threshold: int = 1,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True,
    debug_pages: bool = False,
    fallback_on_all_blank: bool = True,
) -> int:
    reader = PdfReader(str(src_pdf))
    writer = PdfWriter()
    removed = 0
    kept = 0
    for p in reader.pages:
        if is_blank_page(
            p,
            text_len_threshold=text_len_threshold,
            min_alnum_chars=min_alnum_chars,
            min_alnum_ratio=min_alnum_ratio,
            min_stream_bytes=min_stream_bytes,
            treat_any_image_as_nonblank=treat_any_image_as_nonblank,
            debug_pages=debug_pages,
        ):
            removed += 1
            continue
        writer.add_page(p)
        kept += 1

    # Fallback: if everything looked blank (kept == 0), keep original file
    if kept == 0:
        if debug_pages:
            logger.debug(
                "All pages classified blank for part; fallback_on_all_blank=%s",
                fallback_on_all_blank,
            )
        dst_pdf.parent.mkdir(parents=True, exist_ok=True)
        if fallback_on_all_blank:
            try:
                shutil.copy2(src_pdf, dst_pdf)
            except Exception:
                # As a secondary fallback, write an unmodified copy via PdfWriter
                for p in reader.pages:
                    writer.add_page(p)
                _strip_tags_from_writer(writer)
                with dst_pdf.open("wb") as f:
                    writer.write(f)
        else:
            # Write an empty PDF (no pages) to signal removal of all pages
            with dst_pdf.open("wb") as f:
                PdfWriter().write(f)
        return removed

    _strip_tags_from_writer(writer)
    dst_pdf.parent.mkdir(parents=True, exist_ok=True)
    with dst_pdf.open("wb") as f:
        writer.write(f)
    return removed

def _strip_tags_from_writer(writer: PdfWriter) -> None:
    """Remove PDF tagging structures from the writer's catalog and pages.

    This deletes StructTreeRoot/MarkInfo/RoleMap from the catalog and
    clears page-level tagging keys like Tabs/StructParents.
    """
    try:
        root = writer._root_object  # pypdf internal catalog object
        for k in ("/StructTreeRoot", "/MarkInfo", "/RoleMap"):
            if k in root:
                try:
                    del root[k]
                except Exception:
                    pass
        # Ensure not explicitly marked as tagged
        if "/MarkInfo" in root:
            mi = root["/MarkInfo"]
            try:
                if isinstance(mi, DictionaryObject) and NameObject("/Marked") in mi:
                    del mi[NameObject("/Marked")]
            except Exception:
                pass
    except Exception:
        pass

    # Page-level cleanup
    try:
        for page in writer.pages:
            for key in ("/Tabs", "/StructParents"):
                try:
                    if key in page:
                        del page[NameObject(key)]
                except Exception:
                    pass
    except Exception:
        pass

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
    # Collect PDFs case-insensitively (e.g., .pdf, .PDF)
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
            else:
                out_dir_split.mkdir(parents=True, exist_ok=True)
                target = out_dir_split / src.name
                shutil.copy2(src, target)
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
                    dst = (out_dir_clean / p.name)
                    try:
                        removed = remove_blank_pages(
                            p, dst,
                            min_alnum_chars=min_alnum_chars,
                            min_alnum_ratio=min_alnum_ratio,
                            min_stream_bytes=min_stream_bytes,
                            treat_any_image_as_nonblank=treat_any_image_as_nonblank,
                            debug_pages=debug_pages,
                            fallback_on_all_blank=fallback_on_all_blank,
                        )
                    except Exception:
                        logger.exception("Fehler bei Leerseiten-Entfernung für %s", p.name)
                        # Fallback: Original kopieren
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(p, dst)
                            removed = 0
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

def move_to_archive(src: Path, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / src.name
    if target.exists():
        base, ext = src.stem, src.suffix
        i = 1
        while (archive_dir / f"{base}_{i:03d}{ext}").exists():
            i += 1
        target = archive_dir / f"{base}_{i:03d}{ext}"
    try:
        src.replace(target)
    except OSError:
        shutil.copy2(src, target)
        src.unlink(missing_ok=True)
    return target

def main():
    ap = argparse.ArgumentParser(description="PDF-Stapel: splitte alle N Seiten und entferne optional Leerseiten (robust gegen OCR-Rauschen).")
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
    ap.add_argument("--archive-dir", help="Optional: verarbeiteten Original-PDF nach Abschluss hierhin verschieben (Archiv)")
    ap.add_argument("--log-file", help="Optional: Pfad zu einer Logdatei")

    ap.add_argument("--min-alnum", type=int, default=5, help="Mindestanzahl an alphanumerischen Zeichen, damit Seite als 'nicht leer' gilt (Standard: 5)")
    ap.add_argument("--min-alnum-ratio", type=float, default=0.2, help="Mindestanteil alphanumerischer Zeichen (ohne Leerraum), damit Seite als 'nicht leer' gilt (Standard: 0.2)")
    ap.add_argument("--min-bytes", type=int, default=40, help="Mindestanzahl Bytes im Content-Stream, damit Seite als 'nicht leer' gilt (Standard: 40)")
    ap.add_argument("--image-nonblank", action="store_true", help="jede Bildseite als 'nicht leer' werten (Standard: an)")
    ap.add_argument("--no-image-nonblank", dest="image_nonblank", action="store_false", help="Bilder NICHT automatisch als 'nicht leer' werten")
    ap.set_defaults(image_nonblank=True)
    ap.add_argument("--debug-pages", action="store_true", help="Pro Seite Debug-Infos und Entscheidungen ausgeben")
    ap.add_argument("--no-fallback-empty", dest="fallback_on_all_blank", action="store_false", help="Kein Fallback: falls alle Seiten leer sind, keine Originalkopie schreiben (leere PDF)")
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
        in_dir, out_dir_split, out_dir_clean,
        n=args.every, clean=clean,
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
