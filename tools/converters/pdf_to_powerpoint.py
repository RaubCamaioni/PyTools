# pdf, powerpoint, pptx, slides, converter

from pathlib import Path
from typing import Literal
import io
import pymupdf
from pptx import Presentation
from pptx.util import Emu


def pdf_to_powerpoint(pdf: Path, mode: Literal["page_images", "editable_text"] = "page_images", dpi: int = 120) -> Path:
    """Turn each PDF page into a PowerPoint slide: as a full-slide image (looks identical) or as editable text boxes
    (keeps the words, loses the layout).
    """
    dpi = max(50, min(dpi, 200))
    prs = Presentation()
    out = pdf.with_suffix(".pptx")
    blank = prs.slide_layouts[6]

    with pymupdf.open(pdf) as doc:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")
        first = doc[0].rect
        prs.slide_width = Emu(int(first.width / 72 * 914400))
        prs.slide_height = Emu(int(first.height / 72 * 914400))

        for i, page in enumerate(doc):
            if i >= 100:
                break
            slide = prs.slides.add_slide(blank)
            if mode == "page_images":
                pix = page.get_pixmap(dpi=dpi)
                slide.shapes.add_picture(io.BytesIO(pix.tobytes("png")), 0, 0, prs.slide_width, prs.slide_height)
            else:
                scale = 914400 / 72
                for block in page.get_text("blocks"):
                    x0, y0, x1, y1, text = block[:5]
                    text = text.strip()
                    if not text:
                        continue
                    box = slide.shapes.add_textbox(
                        Emu(int(x0 * scale)),
                        Emu(int(y0 * scale)),
                        Emu(int((x1 - x0) * scale)),
                        Emu(int((y1 - y0) * scale)),
                    )
                    box.text_frame.word_wrap = True
                    box.text_frame.text = text
    prs.save(str(out))
    return out
