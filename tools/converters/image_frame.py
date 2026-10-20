# image, border, rounded, corners, circle, frame, profile

from pathlib import Path
from typing import Literal
from PIL import Image, ImageDraw, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_frame(
    image: Path,
    style: Literal["border", "rounded_corners", "circle", "padding_square", "polaroid"] = "rounded_corners",
    size_percent: int = 10,
    color: Literal["white", "black", "transparent"] = "white",
) -> Path:
    """Add a solid border, round the corners, cut a circular avatar, pad the image to a
    square, or give it a Polaroid-style frame. Size is a percentage of the shorter
    side.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGBA")
    short = min(img.size)
    amount = max(1, int(short * max(1, min(size_percent, 50)) / 100))
    fill = {"white": (255, 255, 255, 255), "black": (0, 0, 0, 255), "transparent": (0, 0, 0, 0)}[color]

    if style == "border":
        img = ImageOps.expand(img, border=amount, fill=fill)
    elif style == "rounded_corners":
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=amount, fill=255)
        back = Image.new("RGBA", img.size, fill)
        img = Image.composite(img, back, mask)
    elif style == "circle":
        side = short
        img = ImageOps.fit(img, (side, side), Image.LANCZOS)
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
        back = Image.new("RGBA", (side, side), fill)
        img = Image.composite(img, back, mask)
    elif style == "padding_square":
        side = max(img.size) + 2 * amount
        back = Image.new("RGBA", (side, side), fill)
        back.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
        img = back
    else:
        top = amount
        bottom = amount * 4
        back = Image.new("RGBA", (img.width + 2 * top, img.height + top + bottom), (250, 250, 248, 255))
        back.paste(img, (top, top), img)
        img = back
    transparent = color == "transparent" or style in ("rounded_corners", "circle") and color == "transparent"
    out = image.with_name(
        f"{image.stem}_{style}.png"
        if transparent or style in ("rounded_corners", "circle")
        else f"{image.stem}_{style}.jpg"
    )
    if out.suffix == ".jpg":
        img = img.convert("RGB")
    img.save(out, quality=92)
    return out
