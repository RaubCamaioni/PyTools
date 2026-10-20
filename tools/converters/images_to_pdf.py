# image, jpg, png, pdf, zip, bulk, converter

from pathlib import Path
from typing import Literal
import re
import tempfile
import zipfile
import pymupdf
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic", ".heif", ".avif"}
PAGE_SIZES = {"fit_each_image": None, "a4": (595, 842), "letter": (612, 792)}


def natural_key(p: Path):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", p.name)]


def images_to_pdf(
    images_zip: Path,
    page_size: Literal["fit_each_image", "a4", "letter"] = "fit_each_image",
    margin_points: int = 24,
) -> dict:
    """Combine many images into one PDF, one image per page, ordered by file name.
    Upload a .zip of JPG/PNG/WEBP/HEIC/TIFF files (a single image works too).
    """
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        work = Path(tmp)
        if zipfile.is_zipfile(images_zip):
            with zipfile.ZipFile(images_zip) as zf:
                for member in zf.infolist():
                    if (
                        member.is_dir()
                        or Path(member.filename).suffix.lower() not in IMAGE_EXT
                        or "__MACOSX" in member.filename
                    ):
                        continue
                    target = work / Path(member.filename).name
                    target.write_bytes(zf.read(member))
        else:
            (work / images_zip.name).write_bytes(images_zip.read_bytes())
        files = sorted((p for p in work.iterdir() if p.suffix.lower() in IMAGE_EXT), key=natural_key)
        if not files:
            raise ValueError("No images found (looked for jpg, png, webp, bmp, tiff, gif, heic)")

        doc = pymupdf.open()
        size = PAGE_SIZES[page_size]
        for p in files[:500]:
            with Image.open(p) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                buf = work / (p.stem + "_page.jpg")
                img.save(buf, "JPEG", quality=90)
                w, h = img.size
            if size is None:
                page = doc.new_page(width=w, height=h)
                page.insert_image(page.rect, filename=str(buf))
            else:
                page = doc.new_page(width=size[0], height=size[1])
                m = max(0, margin_points)
                page.insert_image(pymupdf.Rect(m, m, size[0] - m, size[1] - m), filename=str(buf), keep_proportion=True)
        out = Path(f"{images_zip.stem}.pdf")
        doc.save(out, garbage=3, deflate=True)
        doc.close()
    return {
        "file": out,
        "pages": len(files[:500]),
        "order": [p.name for p in files[:20]] + (["..."] if len(files) > 20 else []),
    }
