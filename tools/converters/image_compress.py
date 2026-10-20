# image, compress, optimize, jpg, webp, png

from pathlib import Path
from typing import Literal
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_compress(
    image: Path,
    quality: int = 75,
    output: Literal["same_format", "jpg", "webp", "png"] = "same_format",
    max_dimension: int = 0,
) -> dict:
    """Shrink an image's file size: lower JPEG/WEBP quality, palette-reduce PNG, optionally cap the longest side.
    Returns the file and the size before/after.
    """
    before = image.stat().st_size
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img)
        if max_dimension > 0:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        fmt = (
            (img.format or "PNG").upper()
            if output == "same_format"
            else {"jpg": "JPEG", "webp": "WEBP", "png": "PNG"}[output]
        )
        if fmt not in ("JPEG", "WEBP", "PNG"):
            fmt = "JPEG"
        ext = {"JPEG": ".jpg", "WEBP": ".webp", "PNG": ".png"}[fmt]
        out = image.with_name(f"{image.stem}_compressed{ext}")
        q = max(1, min(quality, 100))

        if fmt == "JPEG":
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(out, "JPEG", quality=q, optimize=True, progressive=True)
        elif fmt == "WEBP":
            img.save(out, "WEBP", quality=q, method=6)
        else:
            if img.mode not in ("P", "L", "1"):
                img = img.convert("RGBA").quantize(colors=256 if q >= 50 else 64, method=Image.Quantize.FASTOCTREE)
            img.save(out, "PNG", optimize=True)

    after = out.stat().st_size
    return {
        "file": out,
        "before_bytes": before,
        "after_bytes": after,
        "saved": f"{(1 - after / before) * 100:.1f}%" if before else "n/a",
    }
