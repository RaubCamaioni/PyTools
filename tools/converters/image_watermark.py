# image, watermark, text, stamp, copyright

from pathlib import Path
from typing import Literal
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_watermark(
    image: Path,
    text: str = "© your name",
    position: Literal["bottom_right", "bottom_left", "top_right", "top_left", "center", "tiled"] = "bottom_right",
    size_percent: int = 5,
    opacity_percent: int = 50,
    color: Literal["white", "black"] = "white",
) -> Path:
    """Stamp a text watermark on a photo: pick a corner, the centre, or tile it diagonally across the whole image. Size
    is a percentage of the image height.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGBA")
    w, h = img.size
    font_px = max(10, round(h * max(1, min(size_percent, 50)) / 100))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_px)
    except OSError:
        font = ImageFont.load_default(size=font_px)
    alpha = round(255 * max(5, min(opacity_percent, 100)) / 100)
    fill = (255, 255, 255, alpha) if color == "white" else (0, 0, 0, alpha)
    shadow = (0, 0, 0, alpha // 2) if color == "white" else (255, 255, 255, alpha // 2)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    pad = max(8, font_px // 2)

    if position == "tiled":
        tile = Image.new("RGBA", (tw + pad * 4, th + pad * 4), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((pad * 2 - left, pad * 2 - top), text, font=font, fill=fill)
        tile = tile.rotate(30, expand=True)
        for y in range(-tile.height, h + tile.height, tile.height):
            for x in range(-tile.width, w + tile.width, tile.width):
                layer.alpha_composite(tile, (x, y))
    else:
        spots = {
            "bottom_right": (w - tw - pad, h - th - pad),
            "bottom_left": (pad, h - th - pad),
            "top_right": (w - tw - pad, pad),
            "top_left": (pad, pad),
            "center": ((w - tw) // 2, (h - th) // 2),
        }
        x, y = spots[position]
        draw.text((x - left + 2, y - top + 2), text, font=font, fill=shadow)
        draw.text((x - left, y - top), text, font=font, fill=fill)

    result = Image.alpha_composite(img, layer)
    suffix = image.suffix.lower() if image.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") else ".jpg"
    out = image.with_name(f"{image.stem}_watermarked{suffix}")
    if suffix in (".jpg", ".jpeg"):
        result = result.convert("RGB")
        result.save(out, quality=92)
    else:
        result.save(out)
    return out
