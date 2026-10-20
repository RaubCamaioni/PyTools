# pdf, watermark, stamp, page, numbers

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_watermark(
    pdf: Path,
    text: str = "CONFIDENTIAL",
    style: Literal["diagonal_watermark", "header", "footer", "page_numbers"] = "diagonal_watermark",
    font_size: int = 48,
    opacity: float = 0.25,
) -> Path:
    """Stamp text on every page of a PDF as a large diagonal watermark, a header, a footer, or add 'Page X of Y'
    numbering.
    """
    opacity = max(0.05, min(opacity, 1.0))
    with pymupdf.open(pdf) as doc:
        total = doc.page_count
        for i, page in enumerate(doc, 1):
            rect = page.rect
            if style == "page_numbers":
                label = f"Page {i} of {total}"
                page.insert_text(
                    (rect.width / 2 - len(label) * 3, rect.height - 24),
                    label,
                    fontsize=10,
                    color=(0.3, 0.3, 0.3),
                    fontname="helv",
                )
            elif style == "header":
                page.insert_text(
                    (36, 30), text, fontsize=max(6, min(font_size, 24)), color=(0.3, 0.3, 0.3), fontname="helv"
                )
            elif style == "footer":
                page.insert_text(
                    (36, rect.height - 24),
                    text,
                    fontsize=max(6, min(font_size, 24)),
                    color=(0.3, 0.3, 0.3),
                    fontname="helv",
                )
            else:
                size = max(8, min(font_size, 200))
                width = pymupdf.get_text_length(text, fontname="helv", fontsize=size)
                box = pymupdf.Rect(0, 0, width + 20, size * 1.4)
                box = box + (
                    (rect.width - box.width) / 2,
                    (rect.height - box.height) / 2,
                    (rect.width - box.width) / 2,
                    (rect.height - box.height) / 2,
                )
                page.insert_textbox(
                    box,
                    text,
                    fontsize=size,
                    fontname="helv",
                    color=(0.5, 0.5, 0.5),
                    fill_opacity=opacity,
                    align=pymupdf.TEXT_ALIGN_CENTER,
                    rotate=0,
                    morph=(box.tl + (box.width / 2, box.height / 2), pymupdf.Matrix(45)),
                )
        out = Path(f"{pdf.stem}_{style}.pdf")
        doc.save(out, garbage=3, deflate=True)
    return out
