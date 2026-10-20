# image, filter, sepia, invert, blur, sharpen, vintage, effect

from pathlib import Path
from typing import Literal
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_filters(
    image: Path,
    effect: Literal[
        "grayscale",
        "sepia",
        "invert",
        "posterize",
        "solarize",
        "blur",
        "sharpen",
        "edge_enhance",
        "emboss",
        "contour",
        "vintage",
        "high_contrast",
        "brighten",
        "darken",
        "saturate",
        "desaturate",
        "pixel_art",
    ] = "sepia",
    strength: int = 50,
) -> Path:
    """Apply a photo effect: grayscale, sepia, invert, posterize, solarize, blur,
    sharpen, emboss, contour, vintage, contrast, brightness, saturation or a
    pixel-art look. Strength is 0 to 100.
    """
    k = max(0, min(strength, 100)) / 100
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    if effect == "grayscale":
        img = ImageOps.grayscale(img).convert("RGB")
    elif effect == "sepia":
        gray = ImageOps.grayscale(img)
        img = Image.blend(img, ImageOps.colorize(gray, "#2b1a0e", "#f7e3c3"), 0.4 + 0.6 * k)
    elif effect == "invert":
        img = ImageOps.invert(img)
    elif effect == "posterize":
        img = ImageOps.posterize(img, max(1, 8 - int(k * 6)))
    elif effect == "solarize":
        img = ImageOps.solarize(img, threshold=int(255 - k * 200))
    elif effect == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5 + k * 15))
    elif effect == "sharpen":
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(50 + k * 250), threshold=2))
    elif effect == "edge_enhance":
        img = img.filter(ImageFilter.EDGE_ENHANCE_MORE if k > 0.5 else ImageFilter.EDGE_ENHANCE)
    elif effect == "emboss":
        img = img.filter(ImageFilter.EMBOSS)
    elif effect == "contour":
        img = img.filter(ImageFilter.CONTOUR)
    elif effect == "vintage":
        faded = ImageEnhance.Color(img).enhance(0.6)
        faded = ImageEnhance.Contrast(faded).enhance(0.85)
        warm = ImageOps.colorize(ImageOps.grayscale(faded), "#3a2a1a", "#ffe9c4")
        img = Image.blend(faded, warm, 0.25 + 0.4 * k)
    elif effect == "high_contrast":
        img = ImageEnhance.Contrast(img).enhance(1 + k * 1.5)
    elif effect == "brighten":
        img = ImageEnhance.Brightness(img).enhance(1 + k)
    elif effect == "darken":
        img = ImageEnhance.Brightness(img).enhance(1 - k * 0.8)
    elif effect == "saturate":
        img = ImageEnhance.Color(img).enhance(1 + k * 2)
    elif effect == "desaturate":
        img = ImageEnhance.Color(img).enhance(1 - k)
    else:
        factor = max(2, int(2 + k * 30))
        small = img.resize((max(1, img.width // factor), max(1, img.height // factor)), Image.NEAREST)
        img = small.resize(img.size, Image.NEAREST).quantize(colors=32).convert("RGB")
    out = image.with_name(
        f"{image.stem}_{effect}.jpg" if image.suffix.lower() in (".jpg", ".jpeg") else f"{image.stem}_{effect}.png"
    )
    img.save(out, quality=92)
    return out
