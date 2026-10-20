# pdf, crop, margins, trim

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_crop(
    pdf: Path,
    mode: Literal["auto_trim_white_margins", "margins_in_mm"] = "auto_trim_white_margins",
    top_mm: float = 10,
    bottom_mm: float = 10,
    left_mm: float = 10,
    right_mm: float = 10,
) -> Path:
    """Crop every page of a PDF: automatically trim the white margins around the
    content, or cut the given millimetres from each edge.
    """
    pt = 72 / 25.4
    with pymupdf.open(pdf) as doc:
        for page in doc:
            rect = page.rect
            if mode == "margins_in_mm":
                box = pymupdf.Rect(
                    rect.x0 + left_mm * pt, rect.y0 + top_mm * pt, rect.x1 - right_mm * pt, rect.y1 - bottom_mm * pt
                )
            else:
                words = page.get_text("words")
                drawings = [d["rect"] for d in page.get_drawings()]
                images = [page.get_image_bbox(item) for item in page.get_images(full=True)]
                boxes = [pymupdf.Rect(w[:4]) for w in words] + drawings + images
                boxes = [b for b in boxes if not b.is_empty and b.width < rect.width * 1.5]
                if not boxes:
                    continue
                box = boxes[0]
                for b in boxes[1:]:
                    box |= b
                margin = 6
                box = pymupdf.Rect(box.x0 - margin, box.y0 - margin, box.x1 + margin, box.y1 + margin) & rect
            if box.is_empty or box.width < 20 or box.height < 20:
                continue
            page.set_cropbox(box)
        out = pdf.with_name(f"{pdf.stem}_cropped.pdf")
        doc.save(out, garbage=3, deflate=True)
    return out
