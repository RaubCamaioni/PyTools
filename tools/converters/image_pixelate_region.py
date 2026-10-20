# image, blur, pixelate, censor, region, privacy

from pathlib import Path
from typing import Literal
from PIL import Image, ImageFilter, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_pixelate_region(
    image: Path,
    left_percent: float = 25,
    top_percent: float = 25,
    width_percent: float = 50,
    height_percent: float = 50,
    style: Literal["pixelate", "blur", "black_box"] = "pixelate",
    strength: int = 50,
) -> Path:
    """Pixelate, blur or black out a rectangle of an image given as percentages of the
    width and height (so the same numbers work at any resolution): licence plates,
    addresses, faces.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    w, h = img.size
    x0 = int(w * max(0, min(left_percent, 100)) / 100)
    y0 = int(h * max(0, min(top_percent, 100)) / 100)
    x1 = min(w, x0 + int(w * max(1, min(width_percent, 100)) / 100))
    y1 = min(h, y0 + int(h * max(1, min(height_percent, 100)) / 100))
    region = img.crop((x0, y0, x1, y1))
    k = max(1, min(strength, 100))
    if style == "black_box":
        region = Image.new("RGB", region.size, "black")
    elif style == "blur":
        region = region.filter(ImageFilter.GaussianBlur(radius=2 + k / 4))
    else:
        block = max(2, int(min(region.size) / max(2, 40 - k / 3)))
        small = region.resize((max(1, region.width // block), max(1, region.height // block)), Image.NEAREST)
        region = small.resize(region.size, Image.NEAREST)
    img.paste(region, (x0, y0))
    out = image.with_name(f"{image.stem}_{style}.jpg")
    img.save(out, quality=92)
    return out
