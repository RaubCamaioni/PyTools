# image, color blindness, accessibility, simulate, deuteranopia

from pathlib import Path
from typing import Literal
import numpy as np
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

# Machado et al. (2009) severity-1 matrices applied in linear RGB
MATRICES = {
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def color_blindness_simulator(
    image: Path,
    vision: Literal[
        "deuteranopia", "protanopia", "tritanopia", "achromatopsia", "all_four_side_by_side"
    ] = "deuteranopia",
) -> Path:
    """Show how an image, chart or UI looks to people with red-green (deuteranopia,
    protanopia), blue-yellow (tritanopia) or no colour vision, singly or all four
    side by side.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    img.thumbnail((2000, 2000))
    rgb = np.asarray(img).astype(np.float64) / 255
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)

    def simulate(kind: str) -> Image.Image:
        if kind == "achromatopsia":
            lum = linear @ np.array([0.2126, 0.7152, 0.0722])
            sim = np.repeat(lum[:, :, None], 3, axis=2)
        else:
            sim = linear @ np.array(MATRICES[kind]).T
        sim = np.clip(sim, 0, 1)
        srgb = np.where(sim <= 0.0031308, sim * 12.92, 1.055 * sim ** (1 / 2.4) - 0.055)
        return Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8), "RGB")

    if vision == "all_four_side_by_side":
        kinds = ["deuteranopia", "protanopia", "tritanopia", "achromatopsia"]
        tiles = [img] + [simulate(k) for k in kinds]
        w, h = img.size
        from PIL import ImageDraw

        sheet = Image.new("RGB", (w * 5 + 40, h + 24), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (tile, label) in enumerate(zip(tiles, ["original"] + kinds)):
            sheet.paste(tile, (i * (w + 10), 24))
            draw.text((i * (w + 10) + 4, 6), label, fill="black")
        result = sheet
    else:
        result = simulate(vision)
    out = image.with_name(f"{image.stem}_{vision}.png")
    result.save(out)
    return out
