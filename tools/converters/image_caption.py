# image, caption, meme, text, overlay

from pathlib import Path
from typing import Literal
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_caption(
    image: Path,
    top_text: str = "",
    bottom_text: str = "",
    style: Literal["meme", "subtitle", "label_bar"] = "meme",
    size_percent: int = 8,
) -> Path:
    """Write text on an image: meme style (white block capitals with a black outline,
    top and bottom), a subtitle at the bottom, or a bar with a label below the
    picture.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    font_px = max(12, int(img.height * max(2, min(size_percent, 30)) / 100))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_px)
    except OSError:
        font = ImageFont.load_default(size=font_px)

    if style == "label_bar":
        bar = font_px * 2
        canvas = Image.new("RGB", (img.width, img.height + bar), "white")
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        text = (top_text + " " + bottom_text).strip()
        w = draw.textlength(text, font=font)
        draw.text(((img.width - w) / 2, img.height + bar / 2 - font_px / 2), text, font=font, fill="black")
        img = canvas
    else:
        draw = ImageDraw.Draw(img)
        lines = []
        if style == "meme":
            lines = [(top_text.upper(), "top"), (bottom_text.upper(), "bottom")]
        else:
            lines = [((top_text + " " + bottom_text).strip(), "bottom")]
        for text, where in lines:
            if not text:
                continue
            wrapped = wrap(text, font, draw, img.width * 0.92)
            line_h = font_px * 1.15
            y = font_px * 0.4 if where == "top" else img.height - line_h * len(wrapped) - font_px * 0.4
            for line in wrapped:
                w = draw.textlength(line, font=font)
                x = (img.width - w) / 2
                outline = max(1, font_px // 15)
                draw.text((x, y), line, font=font, fill="white", stroke_width=outline, stroke_fill="black")
                y += line_h
    out = image.with_name(f"{image.stem}_{style}.jpg")
    img.save(out, quality=92)
    return out


def wrap(text: str, font, draw, max_width: float) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
