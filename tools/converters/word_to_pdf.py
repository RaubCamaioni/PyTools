# word, docx, pdf, document, converter

from pathlib import Path
from typing import Literal
import mammoth
import pymupdf

STYLE = """
body { font-family: sans-serif; font-size: %dpt; line-height: 1.4; }
h1 { font-size: 2em; } h2 { font-size: 1.5em; } h3 { font-size: 1.2em; }
table { border-collapse: collapse; } td, th { border: 0.5pt solid #888; padding: 3pt; }
img { max-width: 100%%; }
pre, code { font-family: monospace; }
"""


def word_to_pdf(
    docx: Path,
    page_size: Literal["a4", "letter"] = "a4",
    font_size: int = 11,
) -> Path:
    """Convert a Word .docx to PDF. Headings, paragraphs, bold/italic, lists, tables and
    embedded images are kept; exact page layout, fonts and headers/footers are not
    (no Office installed in the sandbox).
    """
    with open(docx, "rb") as f:
        result = mammoth.convert_to_html(f)
    html = result.value
    width, height = (595, 842) if page_size == "a4" else (612, 792)
    css = STYLE % max(6, min(font_size, 24))

    story = pymupdf.Story(html=f"<body>{html}</body>", user_css=css)
    out = docx.with_suffix(".pdf")
    writer = pymupdf.DocumentWriter(str(out))
    margin = 56
    box = pymupdf.Rect(margin, margin, width - margin, height - margin)
    more, pages = True, 0
    while more and pages < 1000:
        device = writer.begin_page(pymupdf.Rect(0, 0, width, height))
        more, _ = story.place(box)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    return out
