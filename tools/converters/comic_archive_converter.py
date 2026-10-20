# cbz, cbr, comic, pdf, images, converter

from pathlib import Path
from typing import Literal
import re
import tempfile
import zipfile
import pymupdf

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def comic_archive_converter(file: Path, output: Literal["pdf", "cbz"] = "pdf", dpi: int = 150) -> dict:
    """Convert a comic archive (CBZ, a zip of page images) to PDF, or a PDF into a CBZ
    with one JPEG per page. Pages are ordered by file name.
    """
    if output == "cbz":
        if file.suffix.lower() == ".cbz" or zipfile.is_zipfile(file):
            return {"error": "That is already a CBZ; choose pdf to convert it"}
        out = file.with_suffix(".cbz")
        with pymupdf.open(file) as doc, zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
            for i, page in enumerate(doc, 1):
                zf.writestr(
                    f"page_{i:04d}.jpg", page.get_pixmap(dpi=max(72, min(dpi, 300))).tobytes("jpeg", jpg_quality=88)
                )
            pages = doc.page_count
        return {"file": out, "pages": pages}
    if not zipfile.is_zipfile(file):
        return {"error": "Expected a CBZ (zip) archive of page images"}
    with tempfile.TemporaryDirectory(dir=".") as tmp, zipfile.ZipFile(file) as zf:
        work = Path(tmp)
        names = [n for n in zf.namelist() if Path(n).suffix.lower() in IMAGE_EXT and "__MACOSX" not in n]
        names.sort(key=lambda n: [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", n)])
        if not names:
            return {"error": "No page images found in the archive"}
        doc = pymupdf.open()
        for n in names[:1000]:
            data = zf.read(n)
            pix = pymupdf.Pixmap(data)
            page = doc.new_page(width=pix.width, height=pix.height)
            page.insert_image(page.rect, stream=data)
        out = file.with_suffix(".pdf")
        doc.save(out, garbage=3, deflate=True)
        doc.close()
    return {"file": out, "pages": len(names[:1000])}
