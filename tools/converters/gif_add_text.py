# gif, caption, text, meme, animation

from pathlib import Path
from typing import Literal
from PIL import Image, ImageDraw, ImageFont, ImageSequence


def gif_add_text(
    gif: Path,
    text: str = "when it finally works",
    position: Literal["bottom", "top"] = "bottom",
    size_percent: int = 10,
) -> dict:
    """Put a caption on every frame of an animated GIF (white text with a black outline,
    meme style) and save it as a new GIF.
    """
    with Image.open(gif) as src:
        default = int(src.info.get("duration", 100)) or 100
        frames = [
            (f.convert("RGB"), int(f.info.get("duration", default)) or default) for f in ImageSequence.Iterator(src)
        ]
        loop = src.info.get("loop", 0)
    if not frames:
        return {"error": "No frames found"}
    w, h = frames[0][0].size
    font_px = max(10, int(h * max(3, min(size_percent, 30)) / 100))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_px)
    except OSError:
        font = ImageFont.load_default(size=font_px)
    caption = text.upper()
    out_frames = []
    for frame, _ in frames:
        draw = ImageDraw.Draw(frame)
        words, lines, line = caption.split(), [], ""
        for word in words:
            trial = (line + " " + word).strip()
            if draw.textlength(trial, font=font) <= w * 0.92 or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        y = font_px * 0.3 if position == "top" else h - len(lines) * font_px * 1.15 - font_px * 0.3
        for ln in lines:
            x = (w - draw.textlength(ln, font=font)) / 2
            draw.text((x, y), ln, font=font, fill="white", stroke_width=max(1, font_px // 14), stroke_fill="black")
            y += font_px * 1.15
        out_frames.append(frame.quantize(colors=256, method=Image.Quantize.MEDIANCUT))
    out = gif.with_name(f"{gif.stem}_captioned.gif")
    out_frames[0].save(
        out, save_all=True, append_images=out_frames[1:], duration=[d for _, d in frames], loop=loop, disposal=2
    )
    return {"file": out, "frames": len(frames)}
