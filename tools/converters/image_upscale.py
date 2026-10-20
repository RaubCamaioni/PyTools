# image, upscale, enlarge, sharpen, 2x, 4x

from pathlib import Path
from typing import Literal
from PIL import Image, ImageFilter, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_upscale(
    image: Path,
    factor: Literal["2x", "3x", "4x"] = "2x",
    method: Literal["smooth_lanczos", "sharp_pixel_art"] = "smooth_lanczos",
    sharpen: Literal["yes", "no"] = "yes",
) -> dict:
    """Enlarge an image 2x, 3x or 4x: smooth Lanczos resampling with optional sharpening
    for photos, or nearest-neighbour for pixel art and screenshots. Capped at 8000 px
    a side.
    """
    scale = int(factor[0])
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    w, h = img.size
    cap = max(1, 8000 // max(w, h))
    scale = min(scale, cap) if cap >= 1 else 1
    size = (w * scale, h * scale)
    if method == "sharp_pixel_art":
        result = img.resize(size, Image.NEAREST)
    else:
        result = img.resize(size, Image.LANCZOS)
        if sharpen == "yes":
            result = result.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=3))
    out = image.with_name(f"{image.stem}_{scale}x.png" if result.mode == "RGBA" else f"{image.stem}_{scale}x.jpg")
    result.save(out, quality=94)
    return {"file": out, "from": f"{w}x{h}", "to": f"{size[0]}x{size[1]}"}
