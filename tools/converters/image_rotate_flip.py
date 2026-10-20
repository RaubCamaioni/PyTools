# image, rotate, flip, mirror

from pathlib import Path
from typing import Literal
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_rotate_flip(
    image: Path,
    operation: Literal[
        "rotate_90_clockwise",
        "rotate_90_counterclockwise",
        "rotate_180",
        "flip_horizontal",
        "flip_vertical",
        "auto_orient_from_exif",
        "custom_angle",
    ] = "rotate_90_clockwise",
    angle: float = 0,
) -> Path:
    """Rotate or mirror an image, or fix its orientation from the EXIF tag. custom_angle
    rotates by any angle (counterclockwise) and expands the canvas.
    """
    with Image.open(image) as img:
        img.load()
        if operation == "auto_orient_from_exif":
            result = ImageOps.exif_transpose(img)
        elif operation == "rotate_90_clockwise":
            result = img.transpose(Image.Transpose.ROTATE_270)
        elif operation == "rotate_90_counterclockwise":
            result = img.transpose(Image.Transpose.ROTATE_90)
        elif operation == "rotate_180":
            result = img.transpose(Image.Transpose.ROTATE_180)
        elif operation == "flip_horizontal":
            result = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif operation == "flip_vertical":
            result = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        else:
            result = img.convert("RGBA").rotate(angle, expand=True, resample=Image.BICUBIC)

        suffix = (
            image.suffix.lower()
            if image.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
            else ".png"
        )
        if operation == "custom_angle" and suffix in (".jpg", ".jpeg", ".bmp"):
            suffix = ".png"  # keep the transparent corners
        out = image.with_name(f"{image.stem}_{operation}{suffix}")
        if suffix in (".jpg", ".jpeg") and result.mode not in ("RGB", "L"):
            result = result.convert("RGB")
        result.save(out)
    return out
