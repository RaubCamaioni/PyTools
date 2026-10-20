# image, ascii, art, text, converter

from pathlib import Path
from typing import Literal
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

RAMPS = {
    "detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "simple": "@%#*+=-:. ",
    "blocks": "█▓▒░ ",
}


def image_to_ascii(
    image: Path,
    width: int = 100,
    style: Literal["simple", "detailed", "blocks"] = "simple",
    invert: Literal["no", "yes"] = "no",
) -> Path:
    """Turn an image into ASCII art text (best viewed in a monospace font)."""
    ramp = RAMPS[style]
    if invert == "yes":
        ramp = ramp[::-1]
    width = max(10, min(width, 400))
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img).convert("L")
        height = max(1, round(img.height / img.width * width * 0.5))
        img = img.resize((width, height))
        pixels = list(img.getdata())
    scale = (len(ramp) - 1) / 255
    lines = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        lines.append("".join(ramp[int(p * scale)] for p in row))
    out = image.with_name(f"{image.stem}_ascii.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
