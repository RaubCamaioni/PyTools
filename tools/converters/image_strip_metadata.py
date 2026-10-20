# image, exif, metadata, privacy, remove

from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_strip_metadata(image: Path) -> dict:
    """Remove EXIF, GPS location, camera and all other metadata from a photo (orientation is applied first so the picture still looks right)."""
    before = image.stat().st_size
    with Image.open(image) as img:
        tags = len(img.getexif())
        img = ImageOps.exif_transpose(img)
        clean = Image.new(img.mode, img.size)
        clean.putdata(list(img.getdata()))
        fmt = img.format if img.format in ("JPEG", "PNG", "WEBP", "TIFF", "BMP") else "PNG"
        ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "TIFF": ".tif", "BMP": ".bmp"}[fmt]
        out = image.with_name(f"{image.stem}_clean{ext}")
        if fmt == "JPEG":
            clean.save(out, fmt, quality=95, subsampling="keep" if img.format == "JPEG" else 0)
        else:
            clean.save(out, fmt)
    return {"file": out, "exif_tags_removed": tags, "before_bytes": before, "after_bytes": out.stat().st_size}
