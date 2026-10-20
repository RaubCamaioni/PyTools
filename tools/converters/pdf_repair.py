# pdf, repair, fix, metadata, strip, clean

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_repair(pdf: Path, action: Literal["repair", "strip_metadata", "repair_and_strip"] = "repair") -> dict:
    """Rebuild a damaged PDF (broken cross-reference table, truncated file) by re-saving
    it, and/or remove its metadata (author, title, producer, creation dates, XMP).
    """
    out = pdf.with_name(f"{pdf.stem}_{action}.pdf")
    try:
        doc = pymupdf.open(pdf)
    except Exception as e:  # noqa: BLE001
        return {"error": f"The file could not be opened even in repair mode: {e}"}
    with doc:
        before = dict(doc.metadata or {})
        repaired = bool(getattr(doc, "is_repaired", False))
        if action in ("strip_metadata", "repair_and_strip"):
            doc.set_metadata({})
            doc.del_xml_metadata()
        doc.save(out, garbage=4, deflate=True, clean=True)
    with pymupdf.open(out) as check:
        return {
            "file": out,
            "pages": check.page_count,
            "was_repaired": repaired,
            "metadata_before": {k: v for k, v in before.items() if v},
            "metadata_after": {k: v for k, v in (check.metadata or {}).items() if v},
        }
