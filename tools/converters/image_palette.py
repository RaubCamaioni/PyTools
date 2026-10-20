# image, color, palette, dominant, extract

from pathlib import Path
import colorsys
from PIL import Image, ImageDraw, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_palette(image: Path, colors: int = 6) -> dict:
    """Extract the dominant colours of an image as hex/RGB/HSL with their share of the
    picture, plus a swatch strip PNG.
    """
    colors = max(2, min(colors, 16))
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    img.thumbnail((300, 300))
    quantized = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()[: colors * 3]
    counts = sorted(quantized.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    entries = []
    for count, index in counts:
        r, g, b = palette[index * 3 : index * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        entries.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "rgb": f"rgb({r}, {g}, {b})",
                "hsl": f"hsl({h * 360:.0f}, {s * 100:.0f}%, {l * 100:.0f}%)",
                "share": f"{count / total * 100:.1f}%",
            }
        )
    width = 100 * len(entries)
    strip = Image.new("RGB", (width, 120), "white")
    draw = ImageDraw.Draw(strip)
    for i, e in enumerate(entries):
        draw.rectangle((i * 100, 0, (i + 1) * 100, 100), fill=e["hex"])
        draw.text((i * 100 + 6, 104), e["hex"], fill="black")
    out = image.with_name(f"{image.stem}_palette.png")
    strip.save(out)
    average = tuple(sum(p[i] for p in img.getdata()) // (img.width * img.height) for i in range(3))
    return {"file": out, "colors": entries, "average_color": "#%02x%02x%02x" % average}
