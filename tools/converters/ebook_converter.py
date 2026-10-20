# ebook, epub, mobi, pdf, fb2, cbz, text, converter

from pathlib import Path
from typing import Literal
import pymupdf

PAGE_SIZES = {"a5": (420, 595), "a4": (595, 842), "letter": (612, 792), "kindle_6in": (260, 350)}


def ebook_converter(
    ebook: Path,
    output: Literal["pdf", "text", "html", "markdown"] = "pdf",
    page_size: Literal["a5", "a4", "letter", "kindle_6in"] = "a5",
) -> Path:
    """Convert an EPUB, MOBI, FB2, XPS or CBZ ebook to PDF (reflowed to the chosen page size), plain text, HTML or
    Markdown. DRM-protected books cannot be converted.
    """
    with pymupdf.open(ebook) as doc:
        if doc.is_encrypted:
            raise ValueError("This book is encrypted/DRM protected")
        if output == "pdf":
            width, height = PAGE_SIZES[page_size]
            if doc.is_reflowable:
                doc.layout(width=width, height=height, fontsize=11)
            pdf_bytes = doc.convert_to_pdf()
            out = ebook.with_suffix(".pdf")
            with pymupdf.open("pdf", pdf_bytes) as pdf:
                toc = doc.get_toc()
                if toc:
                    try:
                        pdf.set_toc(toc)
                    except Exception:  # noqa: BLE001 - a bad TOC should not block the conversion
                        pass
                pdf.save(out, garbage=3, deflate=True)
            return out
        if output == "markdown":
            import pymupdf4llm

            content = pymupdf4llm.to_markdown(doc, show_progress=False)
            ext = "md"
        elif output == "html":
            parts = [page.get_text("xhtml") for page in doc]
            content = (
                "<!doctype html>\n<html><head><meta charset='utf-8'></head><body>\n%s\n</body></html>\n"
                % "\n".join(parts)
            )
            ext = "html"
        else:
            content = "\n".join(page.get_text() for page in doc)
            ext = "txt"
    out = ebook.with_suffix("." + ext)
    out.write_text(content, encoding="utf-8")
    return out
