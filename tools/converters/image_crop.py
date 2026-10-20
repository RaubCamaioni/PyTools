# image, crop, cut, aspect

from pathlib import Path
from typing import Literal
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_crop(
    image: Path,
    mode: Literal["aspect_ratio_center", "pixels"] = "aspect_ratio_center",
    aspect: Literal["1_1", "4_3", "3_4", "16_9", "9_16", "3_2", "2_3", "21_9"] = "1_1",
    left: int = 0,
    top: int = 0,
    width: int = 100,
    height: int = 100,
) -> Path:
    """Crop an image to a centred aspect ratio (square, 16:9, 4:3...) or to an exact
    pixel box (left, top, width, height).
    """
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        if mode == "pixels":
            box = (max(0, left), max(0, top), min(w, left + max(1, width)), min(h, top + max(1, height)))
        else:
            aw, ah = (int(x) for x in aspect.split("_"))
            target = aw / ah
            if w / h > target:
                new_w, new_h = round(h * target), h
            else:
                new_w, new_h = w, round(w / target)
            x0, y0 = (w - new_w) // 2, (h - new_h) // 2
            box = (x0, y0, x0 + new_w, y0 + new_h)
        result = img.crop(box)
        suffix = (
            image.suffix.lower()
            if image.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
            else ".png"
        )
        out = image.with_name(f"{image.stem}_crop_{result.size[0]}x{result.size[1]}{suffix}")
        if suffix in (".jpg", ".jpeg") and result.mode not in ("RGB", "L"):
            result = result.convert("RGB")
        result.save(out)
    return out
