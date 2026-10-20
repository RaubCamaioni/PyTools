# text, pdf, markdown, document, converter

from pathlib import Path
from typing import Literal
import html
import pymupdf


def text_to_pdf(
    text_file: Path,
    input_format: Literal["plain_text", "markdown", "html"] = "plain_text",
    page_size: Literal["a4", "letter"] = "a4",
    font_size: int = 11,
) -> Path:
    """Convert a plain text, Markdown or HTML file into a paginated PDF."""
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    width, height = (595, 842) if page_size == "a4" else (612, 792)
    font_size = max(6, min(font_size, 24))

    if input_format == "markdown":
        import markdown

        body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    elif input_format == "html":
        body = text
    else:
        body = "<pre style='white-space:pre-wrap;font-family:monospace'>" + html.escape(text) + "</pre>"

    story = pymupdf.Story(html=f"<body style='font-size:{font_size}pt;font-family:sans-serif'>{body}</body>")
    out = text_file.with_suffix(".pdf")
    writer = pymupdf.DocumentWriter(str(out))
    margin = 50
    box = pymupdf.Rect(margin, margin, width - margin, height - margin)
    more = True
    pages = 0
    while more and pages < 500:
        device = writer.begin_page(pymupdf.Rect(0, 0, width, height))
        more, _ = story.place(box)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    return out
