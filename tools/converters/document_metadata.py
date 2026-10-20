# docx, xlsx, pptx, metadata, author, strip, privacy

from pathlib import Path
from typing import Literal
import datetime


def document_metadata(document: Path, action: Literal["read", "strip"] = "read") -> dict:
    """Read or remove the hidden properties of an Office file (docx, xlsx, pptx):
    author, last modified by, company, dates, revision count, comments. Strip them
    before sharing a file.
    """
    suffix = document.suffix.lower()
    if suffix == ".docx":
        from docx import Document

        obj = Document(str(document))
    elif suffix == ".xlsx":
        from openpyxl import load_workbook

        obj = load_workbook(str(document))
    elif suffix == ".pptx":
        from pptx import Presentation

        obj = Presentation(str(document))
    else:
        return {"error": "Expected a .docx, .xlsx or .pptx file"}
    props = obj.properties if suffix == ".xlsx" else obj.core_properties
    fields = [
        "author",
        "last_modified_by",
        "title",
        "subject",
        "keywords",
        "comments",
        "category",
        "created",
        "modified",
        "revision",
        "identifier",
        "language",
    ]
    before = {f: str(getattr(props, f)) for f in fields if getattr(props, f, None) not in (None, "")}
    if action == "read":
        return {"file": document.name, "properties": before or "none"}
    for f in (
        "author",
        "last_modified_by",
        "title",
        "subject",
        "keywords",
        "comments",
        "category",
        "identifier",
        "language",
    ):
        if hasattr(props, f):
            try:
                setattr(props, f, "" if f != "revision" else 1)
            except (TypeError, ValueError):
                pass
    now = datetime.datetime(2000, 1, 1)
    for f in ("created", "modified", "last_printed"):
        if hasattr(props, f):
            try:
                setattr(props, f, now)
            except (TypeError, ValueError):
                pass
    if hasattr(props, "revision"):
        try:
            props.revision = 1
        except (TypeError, ValueError):
            pass
    out = document.with_name(f"{document.stem}_clean{suffix}")
    obj.save(str(out))
    return {"file": out, "removed": before or "nothing was set"}
