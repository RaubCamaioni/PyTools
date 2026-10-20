# pdf, compare, diff, changes, document

from pathlib import Path
from typing import Literal
import difflib
import pymupdf


def pdf_compare(
    original: Path, modified: Path, output: Literal["unified_diff", "side_by_side_html"] = "unified_diff"
) -> dict:
    """Compare the text of two PDFs page by page and report what changed, as a unified
    diff or a side-by-side HTML report.
    """
    with pymupdf.open(original) as a, pymupdf.open(modified) as b:
        text_a = [a[i].get_text() for i in range(a.page_count)]
        text_b = [b[i].get_text() for i in range(b.page_count)]
    lines_a = [line for page in text_a for line in page.splitlines(keepends=True)]
    lines_b = [line for page in text_b for line in page.splitlines(keepends=True)]
    ratio = difflib.SequenceMatcher(None, "".join(lines_a), "".join(lines_b)).quick_ratio()
    if output == "side_by_side_html":
        out = Path(f"{original.stem}_vs_{modified.stem}.html")
        page = difflib.HtmlDiff(wrapcolumn=90).make_file(lines_a, lines_b, original.name, modified.name, context=True)
        out.write_text(page, encoding="utf-8")
    else:
        out = Path(f"{original.stem}_vs_{modified.stem}.diff")
        diff = "".join(difflib.unified_diff(lines_a, lines_b, original.name, modified.name))
        out.write_text(diff or "The text of both PDFs is identical.\n", encoding="utf-8")
    return {"file": out, "pages": [len(text_a), len(text_b)], "text_similarity_percent": round(ratio * 100, 1)}
