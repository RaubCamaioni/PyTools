# image, png, jpg, webp, heic, gif, bmp, tiff, converter

from pathlib import Path
from typing import Literal
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

FORMATS = {
    "png": "PNG",
    "jpg": "JPEG",
    "webp": "WEBP",
    "gif": "GIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "ico": "ICO",
    "pdf": "PDF",
}


def image_format_converter(
    image: Path,
    output: Literal["png", "jpg", "webp", "gif", "bmp", "tiff", "ico", "pdf"],
    quality: int = 90,
) -> Path:
    """Convert an image between PNG, JPG, WEBP, GIF, BMP, TIFF, ICO and PDF. Reads HEIC/HEIF (iPhone photos), AVIF, PSD
    and most other formats too.
    """
    with Image.open(image) as img:
        img.load()
        fmt = FORMATS[output]
        if fmt in ("JPEG", "BMP", "PDF") and img.mode not in ("RGB", "L"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if "A" in img.getbands():
                background.paste(img.convert("RGBA"), mask=img.convert("RGBA").getchannel("A"))
            else:
                background.paste(img.convert("RGB"))
            img = background
        elif fmt == "GIF" and img.mode not in ("P", "L"):
            img = img.convert("RGBA").quantize(colors=256)
        elif fmt == "ICO":
            img = img.convert("RGBA")
            if max(img.size) > 256:
                img.thumbnail((256, 256))

        out = image.with_name(f"{image.stem}.{output}")
        options = {}
        if fmt in ("JPEG", "WEBP"):
            options["quality"] = max(1, min(quality, 100))
        if fmt == "JPEG":
            options["optimize"] = True
        if fmt == "PNG":
            options["optimize"] = True
        img.save(out, fmt, **options)
    return out
