# image, pdf, jpg, png, document, converter

from pathlib import Path
from typing import Literal
import pymupdf

PAGE_SIZES = {
    "fit_image": None,
    "a4": (595, 842),
    "letter": (612, 792),
    "a4_landscape": (842, 595),
    "letter_landscape": (792, 612),
}


def image_to_pdf(
    image: Path,
    page_size: Literal["fit_image", "a4", "letter", "a4_landscape", "letter_landscape"] = "fit_image",
    margin_points: int = 36,
) -> Path:
    """Put an image (JPG, PNG, WEBP, BMP, TIFF, GIF...) on a PDF page: either sized to
    the image or centred on A4/Letter with a margin.
    """
    doc = pymupdf.open()
    pix = pymupdf.Pixmap(str(image))
    size = PAGE_SIZES[page_size]
    if size is None:
        page = doc.new_page(width=pix.width, height=pix.height)
        page.insert_image(page.rect, pixmap=pix)
    else:
        page = doc.new_page(width=size[0], height=size[1])
        m = max(0, margin_points)
        box = pymupdf.Rect(m, m, size[0] - m, size[1] - m)
        page.insert_image(box, pixmap=pix, keep_proportion=True)
    out = image.with_suffix(".pdf")
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return out
