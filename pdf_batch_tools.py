#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import shutil
from typing import Iterable, Optional
import traceback

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject
try:
    from pypdf.generic import IndirectObject  # type: ignore
except Exception:  # compatibility if symbol not exported
    IndirectObject = None  # type: ignore

ALNUM_RE = re.compile(r"[0-9A-Za-zÄÖÜäöüß]")

def split_every_n_pages(src_pdf: Path, out_dir: Path, n: int = 2) -> list[Path]:
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
        print(
            f"[DEBUG] text_len={len(txt.strip())} alnum={alnum_count} "
            f"alnum_ratio={alnum_ratio:.3f} stream_bytes={stream_bytes}"
        )
        if len(txt.strip()) <= 120 and txt.strip():
            print(f"[DEBUG] text_preview={txt.strip()!r}")
    if alnum_count >= min_alnum_chars and alnum_ratio >= min_alnum_ratio:
        if debug_pages:
            print("[DEBUG] NON-BLANK reason=alnum_threshold")
        return False

    if len(txt.strip()) >= text_len_threshold and alnum_count == 0:
        pass

    if stream_bytes > min_stream_bytes:
        if debug_pages:
            print(f"[DEBUG] NON-BLANK reason=stream_bytes>{min_stream_bytes}")
        return False

    # Resolve resources with inheritance from Parent nodes (only if needed)
    resources = _get_inherited(page, "/Resources")
    if treat_any_image_as_nonblank and page_has_images(resources):
        if debug_pages:
            print("[DEBUG] NON-BLANK reason=image_found")
        return False

    if debug_pages:
        print("[DEBUG] BLANK reason=below_thresholds")
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
            print("[DEBUG] All pages classified blank for part; fallback_on_all_blank=", fallback_on_all_blank)
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
        raise FileNotFoundError(f"Keine PDF in {in_dir} gefunden.")

    total_parts = 0
    total_cleaned = 0
    total_removed_pages = 0

    for idx, src in enumerate(pdfs, start=1):
        print(f"[{idx}/{len(pdfs)}] Splitte {src.name} alle {n} Seiten → {out_dir_split}")
        try:
            parts = split_every_n_pages(src, out_dir_split, n=n)
            total_parts += len(parts)
            print(f"Erzeugt: {len(parts)} Teil-PDFs aus {src.name}")

            if clean and out_dir_clean is not None:
                print(
                    "Entferne Leerseiten →",
                    out_dir_clean,
                    f"(min_alnum={min_alnum_chars}, min_alnum_ratio={min_alnum_ratio}, min_stream_bytes={min_stream_bytes})"
                )
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
                    except Exception as e:
                        print(f"Fehler bei Leerseiten-Entfernung für {p.name}: {e}")
                        traceback.print_exc()
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
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {src.name}: {e}")
            traceback.print_exc()
        finally:
            # Move original to archive after processing attempt
            if archive_dir is not None and src.exists():
                moved_to = move_to_archive(src, archive_dir)
                print(f"Archiviert: {src.name} → {moved_to}")

    print(f"Gesamt erzeugte Teil-PDFs: {total_parts}")
    if clean and out_dir_clean is not None:
        print(f"Gesamt bereinigte PDFs: {total_cleaned}, entfernte Leerseiten gesamt: {total_removed_pages}")

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
    ap.add_argument("--every", type=int, default=2, help="Alle N Seiten splitten (Standard: 2)")
    ap.add_argument("--no-clean", action="store_true", help="keine Leerseiten-Entfernung durchführen")
    ap.add_argument("--archive-dir", help="Optional: verarbeiteten Original-PDF nach Abschluss hierhin verschieben (Archiv)")

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
    clean = not args.no_clean and (out_dir_clean is not None)

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
