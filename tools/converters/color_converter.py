# color, hex, rgb, hsl, cmyk, converter

import colorsys
import re

NAMED = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000", "lime": "#00ff00", "blue": "#0000ff", "yellow": "#ffff00",
    "cyan": "#00ffff", "aqua": "#00ffff", "magenta": "#ff00ff", "fuchsia": "#ff00ff", "silver": "#c0c0c0", "gray": "#808080",
    "grey": "#808080", "maroon": "#800000", "olive": "#808000", "green": "#008000", "purple": "#800080", "teal": "#008080",
    "navy": "#000080", "orange": "#ffa500", "pink": "#ffc0cb", "brown": "#a52a2a", "gold": "#ffd700", "coral": "#ff7f50",
    "salmon": "#fa8072", "tomato": "#ff6347", "violet": "#ee82ee", "indigo": "#4b0082", "turquoise": "#40e0d0",
    "beige": "#f5f5dc", "ivory": "#fffff0", "khaki": "#f0e68c", "lavender": "#e6e6fa", "crimson": "#dc143c",
}


def parse_color(text: str) -> tuple[int, int, int]:
    t = text.strip().lower()
    if t in NAMED:
        t = NAMED[t]
    if m := re.fullmatch(r"#?([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", t):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", t)]
    if t.startswith("rgb") and len(nums) >= 3:
        if "%" in t:
            nums = [n * 2.55 for n in nums[:3]]
        return tuple(max(0, min(255, round(n))) for n in nums[:3])
    if t.startswith("hsl") and len(nums) >= 3:
        h, s, l = nums[0] / 360, nums[1] / 100, nums[2] / 100
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return round(r * 255), round(g * 255), round(b * 255)
    if t.startswith("hsv") or t.startswith("hsb"):
        h, s, v = nums[0] / 360, nums[1] / 100, nums[2] / 100
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return round(r * 255), round(g * 255), round(b * 255)
    if t.startswith("cmyk") and len(nums) >= 4:
        c, m_, y, k = [n / 100 for n in nums[:4]]
        return round(255 * (1 - c) * (1 - k)), round(255 * (1 - m_) * (1 - k)), round(255 * (1 - y) * (1 - k))
    if len(nums) == 3 and all(0 <= n <= 255 for n in nums):
        return tuple(round(n) for n in nums)
    raise ValueError(f"Could not parse color '{text}'. Try #ff8800, rgb(255,136,0), hsl(32,100%,50%), cmyk(0,47,100,0) or a name like coral.")


def color_converter(color: str = "#ff8800") -> dict:
    """Convert a color between HEX, RGB, HSL, HSV/HSB and CMYK, with luminance and contrast against black and white. Accepts any of those formats or a CSS color name."""
    r, g, b = parse_color(color)
    rf, gf, bf = r / 255, g / 255, b / 255
    h, l, s = colorsys.rgb_to_hls(rf, gf, bf)
    hv, sv, v = colorsys.rgb_to_hsv(rf, gf, bf)
    k = 1 - max(rf, gf, bf)
    if k == 1:
        c = m = y = 0.0
    else:
        c, m, y = (1 - rf - k) / (1 - k), (1 - gf - k) / (1 - k), (1 - bf - k) / (1 - k)

    def lin(ch: float) -> float:
        return ch / 12.92 if ch <= 0.03928 else ((ch + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * lin(rf) + 0.7152 * lin(gf) + 0.0722 * lin(bf)
    contrast_white = round((1.05) / (luminance + 0.05), 2)
    contrast_black = round((luminance + 0.05) / 0.05, 2)
    gray = round(0.299 * r + 0.587 * g + 0.114 * b)

    return {
        "hex": f"#{r:02x}{g:02x}{b:02x}",
        "rgb": f"rgb({r}, {g}, {b})",
        "rgb_percent": f"rgb({rf*100:.1f}%, {gf*100:.1f}%, {bf*100:.1f}%)",
        "hsl": f"hsl({h*360:.0f}, {s*100:.0f}%, {l*100:.0f}%)",
        "hsv": f"hsv({hv*360:.0f}, {sv*100:.0f}%, {v*100:.0f}%)",
        "cmyk": f"cmyk({c*100:.0f}%, {m*100:.0f}%, {y*100:.0f}%, {k*100:.0f}%)",
        "decimal": (r << 16) + (g << 8) + b,
        "grayscale_hex": f"#{gray:02x}{gray:02x}{gray:02x}",
        "inverted_hex": f"#{255-r:02x}{255-g:02x}{255-b:02x}",
        "relative_luminance": round(luminance, 4),
        "contrast_vs_white": contrast_white,
        "contrast_vs_black": contrast_black,
        "readable_text_color": "black" if contrast_black >= contrast_white else "white",
    }
