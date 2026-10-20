# pdf, page size, a4, letter, resize, scale, blank pages

from pathlib import Path
from typing import Literal
import pymupdf

SIZES = {"a4": (595, 842), "letter": (612, 792), "a5": (420, 595), "a3": (842, 1191), "legal": (612, 1008)}


def pdf_page_size(
    pdf: Path,
    action: Literal["resize_pages", "add_blank_page", "pad_to_even_page_count"] = "resize_pages",
    size: Literal["a4", "letter", "a5", "a3", "legal"] = "a4",
    orientation: Literal["keep", "portrait", "landscape"] = "keep",
    blank_page_position: int = 1,
) -> dict:
    """Scale every page onto a standard paper size (content kept proportional and
    centred), insert a blank page at a position (1 = before the first page), or pad
    the document to an even page count for double-sided printing.
    """
    with pymupdf.open(pdf) as src:
        if action == "resize_pages":
            w, h = SIZES[size]
            result = pymupdf.open()
            for page in src:
                landscape = orientation == "landscape" or (orientation == "keep" and page.rect.width > page.rect.height)
                pw, ph = (h, w) if landscape else (w, h)
                new = result.new_page(width=pw, height=ph)
                new.show_pdf_page(new.rect, src, page.number)
            out = pdf.with_name(f"{pdf.stem}_{size}.pdf")
            result.save(out, garbage=3, deflate=True)
            pages = result.page_count
            result.close()
        else:
            if action == "pad_to_even_page_count":
                if src.page_count % 2:
                    src.insert_page(-1, width=src[-1].rect.width, height=src[-1].rect.height)
            else:
                at = max(0, min(blank_page_position - 1, src.page_count))
                ref = src[min(at, src.page_count - 1)]
                src.insert_page(at, width=ref.rect.width, height=ref.rect.height)
            out = pdf.with_name(f"{pdf.stem}_{action}.pdf")
            src.save(out, garbage=3, deflate=True)
            pages = src.page_count
    return {"file": out, "pages": pages}
