# pdf, rotate, pages

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_rotate(
    pdf: Path,
    angle: Literal["90", "180", "270"] = "90",
    pages: str = "all",
) -> Path:
    """Rotate all pages of a PDF, or only the listed pages (1,3,5-7), clockwise by 90,
    180 or 270 degrees.
    """
    degrees = int(angle)
    with pymupdf.open(pdf) as doc:
        targets = set(range(doc.page_count))
        if pages.strip().lower() != "all":
            targets = set()
            for part in pages.replace(" ", "").split(","):
                if "-" in part:
                    a, b = part.split("-", 1)
                    targets.update(range(int(a) - 1, int(b)))
                elif part:
                    targets.add(int(part) - 1)
        for i in targets:
            if 0 <= i < doc.page_count:
                page = doc[i]
                page.set_rotation((page.rotation + degrees) % 360)
        out = Path(f"{pdf.stem}_rotated.pdf")
        doc.save(out, garbage=3, deflate=True)
    return out
