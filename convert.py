#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import pikepdf
from pikepdf import ObjectStreamMode
from pikepdf import Dictionary, Stream, Array

def scrub_markinfo_anywhere(pdf: pikepdf.Pdf) -> None:
    visited = set()

    def _walk(obj):
        # Indirekte Objekte sauber dereferenzieren + Zyklen vermeiden
        try:
            if getattr(obj, "is_indirect", False):
                key = obj.objgen
                if key in visited:
                    return
                visited.add(key)
                obj = pdf.get_object(key)
        except Exception:
            pass

        if isinstance(obj, (Dictionary, Stream)):
            # /MarkInfo auf dieser Ebene entfernen
            if "/MarkInfo" in obj:
                del obj["/MarkInfo"]
            # Rekursiv durch Werte laufen
            for k in list(obj.keys()):
                try:
                    _walk(obj[k])
                except Exception:
                    pass
        elif isinstance(obj, Array):
            for item in list(obj):
                try:
                    _walk(item)
                except Exception:
                    pass

    _walk(pdf.Root)


def strip_tags(pdf: pikepdf.Pdf) -> None:
    """
    Entfernt den Strukturbaum (Tags) und markiert das Dokument als 'untagged'.
    """
    root = pdf.Root  # Dokumentkatalog (/Catalog)

    # 1) Strukturbaum und begleitende Maps entfernen
    if "/StructTreeRoot" in root:
        del root["/StructTreeRoot"]
    for k in ("/RoleMap", "/ClassMap"):
        if k in root:
            del root[k]

    # # 2) MarkInfo so setzen, dass das Dokument NICHT als 'tagged' gilt
    # mi = root.get("/MarkInfo", None)
    # if not isinstance(mi, pikepdf.Dictionary):
    #     root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": False})
    # else:
    #     mi["/Marked"] = False
    #     for k in ("/Suspects", "/UserProperties"):
    #         if k in mi:
    #             del mi[k]

    # 2) MarkInfo komplett entfernen
    if "/MarkInfo" in root:
        del root["/MarkInfo"]

    # 3) (Optional) Auf Seitenebene /StructParents entfernen
    #    Nicht zwingend erforderlich – nur Aufräumen, wenn vorhanden.
    try:
        for page in pdf.pages:
            pobj = page.obj
            if "/StructParents" in pobj:
                del pobj["/StructParents"]
            # Auch Annotations können /StructParent tragen
            if "/Annots" in pobj:
                for annot in list(pobj["/Annots"]):
                    try:
                        aobj = (
                            pdf.get_object(annot.objgen)
                            if getattr(annot, "is_indirect", False)
                            else annot
                        )
                        if isinstance(aobj, pikepdf.Dictionary) and "/StructParent" in aobj:
                            del aobj["/StructParent"]
                    except Exception:
                        # Defensive: einzelne problematische Annots überspringen
                        pass
    except Exception:
        # Falls ein exotisches Seitendaten-Layout dazwischenfunkt,
        # genügt Schritt 1 & 2 bereits zum "Untagged"-Status.
        pass
    
    scrub_markinfo_anywhere(pdf)

def to_pdf14_untagged(input_path: str, output_path: str) -> None:
    """
    Konvertiert ein PDF so, dass:
    - keine Tags mehr vorhanden sind (untagged)
    - PDF-Version genau 1.4 ist (ohne Objekt-Streams)
    """
    with pikepdf.Pdf.open(input_path) as pdf:  # <-- strict=False entfernt
        strip_tags(pdf)

        pdf.save(
            output_path,
            force_version="1.4",
            object_stream_mode=pikepdf.ObjectStreamMode.disable,
            linearize=False,
        )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Konvertiere PDFs zu PDF 1.4 und entferne Tags (ähnlich PDF24)."
    )
    ap.add_argument("input", help="Eingabe-PDF")
    ap.add_argument("output", help="Ausgabe-PDF (wird überschrieben)")
    args = ap.parse_args(argv)

    to_pdf14_untagged(args.input, args.output)


if __name__ == "__main__":
    sys.exit(main())