# gif, resize, optimize, reverse, speed, crop, animation

from pathlib import Path
from typing import Literal
from PIL import Image, ImageSequence


def gif_editor(
    gif: Path,
    operation: Literal[
        "resize", "optimize", "reverse", "change_speed", "loop_once", "boomerang", "drop_every_other_frame"
    ] = "optimize",
    width: int = 320,
    speed_percent: int = 200,
    colors: int = 128,
) -> dict:
    """Edit an animated GIF: resize to a width, shrink the file (fewer colours, dropped frames), reverse it, change its
    speed, make it loop once, or turn it into a boomerang.
    """
    with Image.open(gif) as img:
        default = int(img.info.get("duration", 100)) or 100
        frames = [
            (f.convert("RGBA"), int(f.info.get("duration", default)) or default) for f in ImageSequence.Iterator(img)
        ]
        loop = img.info.get("loop", 0)
    if not frames:
        raise ValueError("No frames found")
    before = gif.stat().st_size

    if operation == "resize":
        w0, h0 = frames[0][0].size
        width = max(8, min(width, 2000))
        height = max(1, round(h0 * width / w0))
        frames = [(f.resize((width, height), Image.LANCZOS), d) for f, d in frames]
    elif operation == "reverse":
        frames = frames[::-1]
    elif operation == "change_speed":
        factor = max(10, min(speed_percent, 2000)) / 100
        frames = [(f, max(20, round(d / factor))) for f, d in frames]
    elif operation == "boomerang":
        frames = frames + frames[-2:0:-1]
    elif operation == "drop_every_other_frame":
        kept = frames[::2]
        frames = [(f, d * 2) for f, d in kept] if len(kept) > 1 else frames
    elif operation == "loop_once":
        loop = 1

    colors = max(2, min(colors, 256))
    out = gif.with_name(f"{gif.stem}_{operation}.gif")
    quantized = [f.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT) for f, _ in frames]
    quantized[0].save(
        out,
        save_all=True,
        append_images=quantized[1:],
        duration=[d for _, d in frames],
        loop=loop,
        optimize=operation == "optimize",
        disposal=2,
    )
    after = out.stat().st_size
    return {
        "file": out,
        "frames": len(frames),
        "size": f"{frames[0][0].size[0]}x{frames[0][0].size[1]}",
        "before_bytes": before,
        "after_bytes": after,
        "change": f"{(after / before - 1) * 100:+.1f}%" if before else "n/a",
    }
