# gradient, css, background, image, color, generator

from pathlib import Path
from typing import Literal
import re
from PIL import Image


def gradient_generator(
    start_color: str = "#ff7e5f",
    end_color: str = "#feb47b",
    direction: Literal["left_to_right", "top_to_bottom", "diagonal", "radial"] = "left_to_right",
    width: int = 1200,
    height: int = 400,
) -> dict:
    """Make a two-colour gradient as a PNG (wallpaper, banner, placeholder) plus the
    matching CSS `background` rule.
    """

    def parse(text: str) -> tuple[int, int, int]:
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", text.strip())
        if m:
            v = m.group(1)
            return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        nums = [min(255, int(n)) for n in re.findall(r"\d+", text)[:3]]
        if len(nums) != 3:
            raise ValueError(f"Could not parse colour '{text}'")
        return tuple(nums)

    try:
        a, b = parse(start_color), parse(end_color)
    except ValueError as e:
        return {"error": str(e)}
    width, height = max(16, min(width, 4000)), max(16, min(height, 4000))
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            if direction == "left_to_right":
                t = x / (width - 1)
            elif direction == "top_to_bottom":
                t = y / (height - 1)
            elif direction == "diagonal":
                t = (x / (width - 1) + y / (height - 1)) / 2
            else:
                dx, dy = (x - width / 2) / (width / 2), (y - height / 2) / (height / 2)
                t = min(1.0, (dx * dx + dy * dy) ** 0.5)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    out = Path("gradient.png")
    img.save(out, optimize=True)
    hex_a, hex_b = "#%02x%02x%02x" % a, "#%02x%02x%02x" % b
    css = {
        "left_to_right": f"background: linear-gradient(90deg, {hex_a}, {hex_b});",
        "top_to_bottom": f"background: linear-gradient(180deg, {hex_a}, {hex_b});",
        "diagonal": f"background: linear-gradient(135deg, {hex_a}, {hex_b});",
        "radial": f"background: radial-gradient(circle, {hex_a}, {hex_b});",
    }[direction]
    return {"file": out, "css": css, "colors": [hex_a, hex_b]}
