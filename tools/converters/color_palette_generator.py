# color, palette, shades, tints, complementary, scheme, generator

from pathlib import Path
from typing import Literal
import colorsys
import re
from PIL import Image, ImageDraw


def color_palette_generator(
    base_color: str = "#3b82f6",
    scheme: Literal[
        "shades_and_tints", "complementary", "analogous", "triadic", "split_complementary", "tetradic", "monochromatic"
    ] = "shades_and_tints",
    count: int = 7,
) -> dict:
    """Build a colour scheme from one base colour (hex or rgb): shades and tints,
    complementary, analogous, triadic, split-complementary, tetradic or
    monochromatic, as hex codes with CSS variables and a swatch PNG.
    """
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", base_color.strip()) or re.fullmatch(
        r"#?([0-9a-fA-F]{3})", base_color.strip()
    )
    if m:
        hexv = m.group(1)
        hexv = "".join(c * 2 for c in hexv) if len(hexv) == 3 else hexv
        r, g, b = (int(hexv[i : i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        nums = re.findall(r"\d+", base_color)
        if len(nums) < 3:
            return {"error": f"Could not parse colour '{base_color}' (use #rrggbb or rgb(r, g, b))"}
        r, g, b = (min(255, int(n)) / 255 for n in nums[:3])
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    count = max(2, min(count, 12))

    def hexof(hh, ll, ss) -> str:
        rr, gg, bb = colorsys.hls_to_rgb(hh % 1, max(0, min(ll, 1)), max(0, min(ss, 1)))
        return "#%02x%02x%02x" % (round(rr * 255), round(gg * 255), round(bb * 255))

    if scheme == "shades_and_tints":
        colors = [hexof(h, i / (count - 1) * 0.9 + 0.05, s) for i in range(count)]
    elif scheme == "monochromatic":
        colors = [hexof(h, l, i / (count - 1)) for i in range(count)]
    else:
        offsets = {
            "complementary": [0, 0.5],
            "analogous": [-1 / 12, 0, 1 / 12],
            "triadic": [0, 1 / 3, 2 / 3],
            "split_complementary": [0, 5 / 12, 7 / 12],
            "tetradic": [0, 0.25, 0.5, 0.75],
        }[scheme]
        colors = [hexof(h + o, l, s) for o in offsets]
    swatch = Image.new("RGB", (100 * len(colors), 130), "white")
    draw = ImageDraw.Draw(swatch)
    for i, c in enumerate(colors):
        draw.rectangle((i * 100, 0, (i + 1) * 100, 100), fill=c)
        draw.text((i * 100 + 8, 108), c, fill="black")
    out = Path(f"palette_{scheme}.png")
    swatch.save(out)
    return {
        "file": out,
        "base": hexof(h, l, s),
        "colors": colors,
        "css_variables": "\n".join(f"--color-{i + 1}: {c};" for i, c in enumerate(colors)),
    }
