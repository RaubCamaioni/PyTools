# pdf, image, jpg, png, converter

from pathlib import Path
from typing import Literal
import pymupdf
import zipfile


def pdf_to_images(
    pdf: Path,
    format: Literal["png", "jpg"] = "png",
    dpi: int = 150,
    pages: str = "all",
) -> Path:
    """Render PDF pages to PNG or JPG images at the chosen DPI. A single page returns
    the image; several pages return a zip.
    """
    dpi = max(36, min(dpi, 300))
    with pymupdf.open(pdf) as doc:
        if pages.strip().lower() == "all":
            selected = list(range(doc.page_count))
        else:
            selected = []
            for part in pages.replace(" ", "").split(","):
                if "-" in part:
                    a, b = part.split("-", 1)
                    selected.extend(range(int(a) - 1, int(b)))
                elif part:
                    selected.append(int(part) - 1)
            selected = [i for i in selected if 0 <= i < doc.page_count]
        if not selected:
            raise ValueError("No pages selected")
        if len(selected) > 50:
            selected = selected[:50]

        if len(selected) == 1:
            out = Path(f"{pdf.stem}_page_{selected[0] + 1}.{format}")
            doc[selected[0]].get_pixmap(dpi=dpi).save(out, jpg_quality=90)
            return out

        out = Path(f"{pdf.stem}_{format}.zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
            for i in selected:
                pix = doc[i].get_pixmap(dpi=dpi)
                zf.writestr(f"{pdf.stem}_page_{i + 1:03d}.{format}", pix.tobytes(format, jpg_quality=90))
    return out
