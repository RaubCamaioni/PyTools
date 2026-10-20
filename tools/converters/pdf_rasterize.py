# pdf, flatten, grayscale, rasterize, scan, image

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_rasterize(
    pdf: Path,
    mode: Literal["flatten", "grayscale", "scanned_look"] = "flatten",
    dpi: int = 150,
) -> dict:
    """Turn every page into a picture of itself: flatten (forms, annotations and layers
    become fixed content, text is no longer selectable), grayscale (black and white
    printing), or a scanned-document look.
    """
    dpi = max(72, min(dpi, 300))
    out = pdf.with_name(f"{pdf.stem}_{mode}.pdf")
    with pymupdf.open(pdf) as src:
        result = pymupdf.open()
        for page in src:
            colorspace = pymupdf.csGRAY if mode in ("grayscale", "scanned_look") else pymupdf.csRGB
            pix = page.get_pixmap(dpi=dpi, colorspace=colorspace, alpha=False)
            if mode == "scanned_look":
                from PIL import Image, ImageEnhance, ImageFilter
                import io

                img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                img = (
                    ImageEnhance.Contrast(img)
                    .enhance(1.3)
                    .filter(ImageFilter.GaussianBlur(0.6))
                    .rotate(0.4, fillcolor=245)
                )
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=70)
                data = buf.getvalue()
            else:
                data = pix.tobytes("jpeg", jpg_quality=85)
            new_page = result.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=data)
        result.save(out, garbage=3, deflate=True)
        result.close()
    return {"file": out, "pages": pymupdf.open(out).page_count, "bytes": out.stat().st_size}
