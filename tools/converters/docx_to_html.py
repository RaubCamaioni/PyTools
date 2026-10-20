# word, docx, html, markdown, document, converter

from pathlib import Path
from typing import Literal
import html
import mammoth


def docx_to_html(docx: Path, output: Literal["html", "markdown"] = "html") -> Path:
    """Convert a Word .docx to clean HTML (images embedded, headings/lists/tables kept) or to Markdown, using semantic
    styles rather than pixel layout.
    """
    with open(docx, "rb") as f:
        if output == "markdown":
            result = mammoth.convert_to_markdown(f)
            out = docx.with_suffix(".md")
            out.write_text(result.value, encoding="utf-8")
            return out
        result = mammoth.convert_to_html(f)

    page = (
        "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(docx.stem)}</title>"
        "<style>body{max-width:46rem;margin:2rem auto;padding:0 1rem;font-family:system-ui,sans-serif;line-height:1.5}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3rem .6rem}img{max-width:100%}</style>"
        f"</head><body>\n{result.value}\n</body></html>\n"
    )
    out = docx.with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    return out
