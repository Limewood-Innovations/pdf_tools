#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from typing import Iterable, Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

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

def page_has_images(resources: Optional[DictionaryObject]) -> bool:
    if not resources:
        return False
    xobj_key = NameObject("/XObject")
    if xobj_key not in resources:
        return False
    xobjs = resources[xobj_key]
    try:
        for _, xobj in xobjs.items():
            try:
                subtype = xobj.get("/Subtype")
                if subtype == "/Image":
                    return True
                if subtype == "/Form" and page_has_images(xobj.get("/Resources")):
                    return True
            except Exception:
                return True
    except Exception:
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
    treat_any_image_as_nonblank: bool = True
) -> bool:
    try:
        txt = page.extract_text() or ""
    except Exception:
        txt = ""

    alnum_count = count_alnum(txt)
    non_ws_chars = sum(1 for c in txt if not c.isspace())
    alnum_ratio = (alnum_count / non_ws_chars) if non_ws_chars else 0.0

    # print(
    #     "Debug: Seite Textlänge=", len(txt.strip()),
    #     "Alnum=", alnum_count,
    #     "AlnumRatio=", f"{alnum_ratio:.3f}",
    #     "StreamBytes=", content_stream_bytes(page)
    # )
    # print(f"Debug: Textvorschau: {txt.strip()!r}")
    if alnum_count >= min_alnum_chars and alnum_ratio >= min_alnum_ratio:
        print("######### NON BLANK: Seite ist nicht leer (Alnum-Kriterium erfüllt)")
        return False

    if len(txt.strip()) >= text_len_threshold and alnum_count == 0:
        pass

    resources = page.get("/Resources")
    if treat_any_image_as_nonblank and page_has_images(resources):
        print("######### NON BLANK: Seite ist nicht leer (Bild gefunden)")
        return False

    if content_stream_bytes(page) > min_stream_bytes:
        print(f'######### NON BLANK: Seite ist nicht leer (Content-Stream zu groß) {content_stream_bytes(page)} > {min_stream_bytes}')
        return False

    print("----------- BLANK: Seite ist leer")
    return True

def remove_blank_pages(
    src_pdf: Path,
    dst_pdf: Path,
    text_len_threshold: int = 1,
    min_alnum_chars: int = 5,
    min_alnum_ratio: float = 0.2,
    min_stream_bytes: int = 40,
    treat_any_image_as_nonblank: bool = True
) -> int:
    reader = PdfReader(str(src_pdf))
    writer = PdfWriter()
    removed = 0
    for p in reader.pages:
        if is_blank_page(
            p,
            text_len_threshold=text_len_threshold,
            min_alnum_chars=min_alnum_chars,
            min_alnum_ratio=min_alnum_ratio,
            min_stream_bytes=min_stream_bytes,
            treat_any_image_as_nonblank=treat_any_image_as_nonblank
        ):
            removed += 1
            continue
        writer.add_page(p)
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
    treat_any_image_as_nonblank: bool = True
):
    pdfs: Iterable[Path] = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Keine PDF in {in_dir} gefunden.")
    if len(pdfs) > 1:
        print(f"Warnung: {len(pdfs)} PDFs gefunden; verarbeite nur die erste: {pdfs[0].name}")
    src = pdfs[0]

    print(f"Splitte {src.name} alle {n} Seiten → {out_dir_split}")
    parts = split_every_n_pages(src, out_dir_split, n=n)
    print(f"Erzeugt: {len(parts)} Teil-PDFs")

    if clean and out_dir_clean is not None:
        print(
            "Entferne Leerseiten →",
            out_dir_clean,
            f"(min_alnum={min_alnum_chars}, min_alnum_ratio={min_alnum_ratio}, min_stream_bytes={min_stream_bytes})"
        )
        cleaned_count = 0
        total_removed = 0
        for p in parts:
            dst = (out_dir_clean / p.name)
            removed = remove_blank_pages(
                p, dst,
                min_alnum_chars=min_alnum_chars,
                min_alnum_ratio=min_alnum_ratio,
                min_stream_bytes=min_stream_bytes,
                treat_any_image_as_nonblank=treat_any_image_as_nonblank
            )
            total_removed += removed
            cleaned_count += 1
        print(f"Bereinigt: {cleaned_count} PDFs, entfernte Leerseiten gesamt: {total_removed}")

def main():
    ap = argparse.ArgumentParser(description="PDF-Stapel: splitte alle N Seiten und entferne optional Leerseiten (robust gegen OCR-Rauschen).")
    ap.add_argument("--in-dir", required=True, help="Verzeichnis 1 (Quelle) mit der Eingangspdf")
    ap.add_argument("--out-dir-split", required=True, help="Verzeichnis 2 (Ausgabe der Teil-PDFs)")
    ap.add_argument("--out-dir-clean", help="Verzeichnis 3 (optional: bereinigte PDFs ohne Leerseiten)")
    ap.add_argument("--every", type=int, default=2, help="Alle N Seiten splitten (Standard: 2)")
    ap.add_argument("--no-clean", action="store_true", help="keine Leerseiten-Entfernung durchführen")

    ap.add_argument("--min-alnum", type=int, default=5, help="Mindestanzahl an alphanumerischen Zeichen, damit Seite als 'nicht leer' gilt (Standard: 5)")
    ap.add_argument("--min-alnum-ratio", type=float, default=0.2, help="Mindestanteil alphanumerischer Zeichen (ohne Leerraum), damit Seite als 'nicht leer' gilt (Standard: 0.2)")
    ap.add_argument("--min-bytes", type=int, default=40, help="Mindestanzahl Bytes im Content-Stream, damit Seite als 'nicht leer' gilt (Standard: 40)")
    ap.add_argument("--image-nonblank", action="store_true", help="jede Bildseite als 'nicht leer' werten (Standard: an)")
    ap.add_argument("--no-image-nonblank", dest="image_nonblank", action="store_false", help="Bilder NICHT automatisch als 'nicht leer' werten")
    ap.set_defaults(image_nonblank=True)

    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir_split = Path(args.out_dir_split)
    out_dir_clean = Path(args.out_dir_clean) if args.out_dir_clean else None
    clean = not args.no_clean and (out_dir_clean is not None)

    process(
        in_dir, out_dir_split, out_dir_clean,
        n=args.every, clean=clean,
        min_alnum_chars=args.min_alnum,
        min_alnum_ratio=args.min_alnum_ratio,
        min_stream_bytes=args.min_bytes,
        treat_any_image_as_nonblank=args.image_nonblank
    )

if __name__ == "__main__":
    main()
