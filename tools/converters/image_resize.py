# image, resize, scale, thumbnail

from pathlib import Path
from typing import Literal
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_resize(
    image: Path,
    width: int = 800,
    height: int = 0,
    mode: Literal["fit_inside", "exact", "fill_and_crop", "percent"] = "fit_inside",
) -> Path:
    """Resize an image. fit_inside keeps the aspect ratio within width x height (0 =
    unlimited); exact stretches; fill_and_crop covers the box and crops the centre;
    percent scales by width%.
    """
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        if mode == "percent":
            factor = max(1, width) / 100
            size = (max(1, round(w * factor)), max(1, round(h * factor)))
            result = img.resize(size, Image.LANCZOS)
        elif mode == "exact":
            size = (max(1, width), max(1, height or round(h * width / w)))
            result = img.resize(size, Image.LANCZOS)
        elif mode == "fill_and_crop":
            size = (max(1, width), max(1, height or width))
            result = ImageOps.fit(img, size, Image.LANCZOS)
        else:
            box = (width if width > 0 else 10**6, height if height > 0 else 10**6)
            result = img.copy()
            result.thumbnail(box, Image.LANCZOS)

        suffix = (
            image.suffix.lower()
            if image.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
            else ".png"
        )
        out = image.with_name(f"{image.stem}_{result.size[0]}x{result.size[1]}{suffix}")
        if suffix in (".jpg", ".jpeg") and result.mode not in ("RGB", "L"):
            result = result.convert("RGB")
        result.save(out)
    return out
