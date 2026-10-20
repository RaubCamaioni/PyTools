# text, diff, compare

from pathlib import Path
from typing import Literal
import difflib


def text_diff(
    original: Path,
    modified: Path,
    format: Literal["unified", "side_by_side_html", "context"] = "unified",
) -> Path:
    """Compare two text files and produce a unified diff, a context diff or a
    side-by-side HTML report.
    """
    a = original.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    b = modified.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

    if format == "side_by_side_html":
        out = Path("diff.html")
        page = difflib.HtmlDiff(wrapcolumn=80).make_file(a, b, original.name, modified.name, context=True, numlines=3)
        out.write_text(page, encoding="utf-8")
        return out

    if format == "context":
        lines = difflib.context_diff(a, b, fromfile=original.name, tofile=modified.name)
    else:
        lines = difflib.unified_diff(a, b, fromfile=original.name, tofile=modified.name)
    diff = "".join(lines)
    if not diff:
        diff = "Files are identical.\n"
    out = Path("diff.txt")
    out.write_text(diff, encoding="utf-8")
    return out
