# image, bulk, batch, resize, convert, zip

from pathlib import Path
from typing import Literal
import tempfile
import zipfile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic", ".heif", ".avif"}


def image_bulk_resize(
    images_zip: Path,
    max_width: int = 1600,
    max_height: int = 1600,
    output_format: Literal["keep", "jpg", "png", "webp"] = "keep",
    quality: int = 85,
) -> dict:
    """Resize and/or convert every image in a zip at once (fit inside max width x
    height, aspect kept, never enlarged), returning a zip. HEIC photos come out as
    JPG by default.
    """
    quality = max(1, min(quality, 100))
    converted, skipped = 0, []
    out = images_zip.with_name(f"{images_zip.stem}_resized.zip")
    with tempfile.TemporaryDirectory(dir=".") as tmp, zipfile.ZipFile(images_zip) as src, zipfile.ZipFile(
        out, "w", zipfile.ZIP_STORED
    ) as dst:
        work = Path(tmp)
        for member in src.infolist():
            name = Path(member.filename)
            if member.is_dir() or name.suffix.lower() not in IMAGE_EXT or "__MACOSX" in member.filename:
                continue
            try:
                with Image.open(src.open(member)) as img:
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((max(16, max_width), max(16, max_height)), Image.LANCZOS)
                    ext = name.suffix.lower()
                    if output_format != "keep":
                        ext = "." + output_format
                    elif ext in (".heic", ".heif", ".avif", ".tif", ".tiff", ".bmp"):
                        ext = ".jpg"
                    if ext in (".jpg", ".jpeg") and img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    target = work / (name.stem + ext)
                    img.save(target, quality=quality)
                dst.write(target, target.name)
                converted += 1
            except Exception as e:  # noqa: BLE001 - one bad file should not stop the batch
                skipped.append(f"{name.name}: {e}")
            if converted >= 500:
                break
    return {"file": out, "images": converted, "skipped": skipped[:20]}
