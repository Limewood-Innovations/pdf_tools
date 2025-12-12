# -*- coding: utf-8 -*-
"""Utility functions shared across PDF processing tools.

This module contains helpers that were originally scattered throughout
``pdf_batch_tools.py``.  They are extracted here so that multiple tool modules
can reuse the same logic without duplication.
"""

import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

# Regular expression to strip ANSI colour codes – used by the logger formatter.
import re
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from *text*.

    Args:
        text: String that may contain colour codes.
    Returns:
        Cleaned string without any ``\x1b[...m`` sequences.
    """
    return _ANSI_ESCAPE_RE.sub("", text)


class StripColorFormatter(logging.Formatter):
    """Logging formatter that removes colour codes from log records.

    The original script used this formatter for file handlers so that log files
    stay human‑readable.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return strip_ansi_codes(message)


def _color_label(label: str) -> str:
    """Return a colour‑coded label for console output.

    ``BLANK`` → red, ``NON-BLANK`` → green, otherwise unchanged.
    """
    if label == "BLANK":
        return f"\033[31m{label}\033[0m"
    if label == "NON-BLANK":
        return f"\033[32m{label}\033[0m"
    return label


def _resolve(obj, max_hops: int = 5):
    """Resolve indirect objects safely with a hop limit.

    This mirrors the helper from the original script and prevents infinite
    loops when ``PdfReader`` returns an ``IndirectObject`` that points to itself.
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
    """Walk up the ``/Parent`` chain to find *name* (e.g. ``/Resources``).

    Args:
        page_like: A ``PageObject`` or raw dictionary representing a page.
        name: The dictionary key to look for, without the leading slash.
    Returns:
        The resolved value or ``None`` if not found.
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
                try:
                    val = cur.get(name_key)
                except Exception:
                    val = None
                if val is not None:
                    return _resolve(val)
                cur = _resolve(cur.get(NameObject("/Parent")))
        except Exception:
            break
        hops += 1
    return None


def content_stream_bytes(page) -> int:
    """Return the total number of bytes in a page's content streams.

    This is used as a heuristic for detecting non‑blank pages.
    """
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
    """Count alphanumeric characters in *text* using the original regex.
    """
    import re
    alnum_re = re.compile(r"[0-9A-Za-zÄÖÜäöüß]")
    return len(alnum_re.findall(text))


def page_has_images(resources: Optional[DictionaryObject]) -> bool:
    """Detect whether a page's resources contain an image XObject.

    The function walks through ``/XObject`` entries and checks the ``/Subtype``
    for ``/Image`` or recursively inspects form XObjects.
    """
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
                try:
                    subtype = x.get(NameObject("/Subtype"))
                except Exception:
                    continue
            else:
                subtype = x.get(NameObject("/Subtype"))
            subval = subtype if isinstance(subtype, str) else (subtype and str(subtype))
            if subval == "/Image":
                return True
            if subval == "/Form":
                nested = _resolve(x.get(NameObject("/Resources"))) if isinstance(x, dict) else None
                if page_has_images(nested):
                    return True
    except Exception:
        return True
    return False


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
