# pdf, compress, shrink, optimize

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_compress(
    pdf: Path,
    level: Literal["lossless", "images_150dpi", "images_96dpi", "images_72dpi"] = "images_150dpi",
) -> dict:
    """Shrink a PDF: lossless cleans unused objects and deflates streams; the image levels also downsample and re-encode pictures as JPEG."""
    before = pdf.stat().st_size
    out = Path(f"{pdf.stem}_compressed.pdf")
    with pymupdf.open(pdf) as doc:
        if level != "lossless":
            dpi = int(level.split("_")[1].replace("dpi", ""))
            doc.rewrite_images(dpi_threshold=dpi + 1, dpi_target=dpi, quality=70, lossy=True, lossless=True, bitonal=True, color=True, gray=True)
        doc.save(out, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
    after = out.stat().st_size
    return {"file": out, "before_bytes": before, "after_bytes": after, "saved": f"{(1 - after / before) * 100:.1f}%" if before else "n/a"}
