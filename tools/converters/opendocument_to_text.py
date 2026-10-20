# odt, ods, odp, libreoffice, openoffice, text, csv, converter

from pathlib import Path
import csv
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}


def opendocument_to_text(document: Path) -> dict:
    """Extract the content of a LibreOffice / OpenOffice file: ODT and ODP become plain
    text, ODS becomes a CSV of the first sheet (the rest are listed). No office suite
    needed.
    """
    if not zipfile.is_zipfile(document):
        return {"error": "Not an OpenDocument file (expected a zip with content.xml)"}
    with zipfile.ZipFile(document) as zf:
        if "content.xml" not in zf.namelist():
            return {"error": "No content.xml inside; not an OpenDocument file"}
        root = ET.fromstring(zf.read("content.xml"))
    tables = root.findall(".//table:table", NS)
    is_sheet = document.suffix.lower() == ".ods" or (tables and not root.findall(".//text:p", NS))
    if is_sheet and tables:
        sheets = {}
        for t in tables:
            rows = []
            for row in t.findall("table:table-row", NS):
                cells = []
                for cell in row.findall("table:table-cell", NS):
                    repeat = int(cell.get(f"{{{NS['table']}}}number-columns-repeated", "1"))
                    value = " ".join("".join(p.itertext()) for p in cell.findall("text:p", NS))
                    cells.extend([value] * min(repeat, 50))
                while cells and cells[-1] == "":
                    cells.pop()
                if cells:
                    rows.append(cells)
            sheets[t.get(f"{{{NS['table']}}}name", "sheet")] = rows
        first = next(iter(sheets))
        out = document.with_suffix(".csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(sheets[first])
        return {"file": out, "sheets": {k: len(v) for k, v in sheets.items()}, "exported_sheet": first}
    paragraphs = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in ("p", "h"):
            text = "".join(node.itertext()).strip()
            if text:
                level = node.get(f"{{{NS['text']}}}outline-level")
                paragraphs.append(("#" * int(level) + " " + text) if tag == "h" and level else text)
    out = document.with_suffix(".txt")
    out.write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")
    return {"file": out, "paragraphs": len(paragraphs), "words": len(re.findall(r"\w+", " ".join(paragraphs)))}
