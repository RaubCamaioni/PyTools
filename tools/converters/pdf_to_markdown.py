# pdf, markdown, html, text, document, converter

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_to_markdown(
    pdf: Path, output: Literal["markdown", "html", "text_by_page"] = "markdown", pages: str = "all"
) -> Path:
    """Convert a PDF to Markdown (headings, lists, tables and emphasis detected), to HTML, or to plain text with a
    marker per page.
    """
    with pymupdf.open(pdf) as doc:
        if pages.strip().lower() == "all":
            indexes = list(range(doc.page_count))
        else:
            indexes = []
            for part in pages.replace(" ", "").split(","):
                a, _, b = part.partition("-")
                if a:
                    indexes.extend(range(int(a) - 1, int(b or a)))
            indexes = [i for i in indexes if 0 <= i < doc.page_count]

        if output == "markdown":
            import pymupdf4llm

            content = pymupdf4llm.to_markdown(doc, pages=indexes, show_progress=False)
            ext = "md"
        elif output == "html":
            parts = [doc[i].get_text("xhtml") for i in indexes]
            content = (
                "<!doctype html>\n<html><head><meta charset='utf-8'><title>%s</title></head>"
                "<body>\n%s\n</body></html>\n"
                % (pdf.stem, "\n<hr>\n".join(parts))
            )
            ext = "html"
        else:
            parts = [f"===== page {i + 1} =====\n{doc[i].get_text()}" for i in indexes]
            content = "\n".join(parts)
            ext = "txt"

    out = pdf.with_suffix("." + ext)
    out.write_text(content, encoding="utf-8")
    return out
