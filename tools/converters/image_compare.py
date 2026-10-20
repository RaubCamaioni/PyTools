# image, compare, diff, difference, similarity

from pathlib import Path
from typing import Literal
from PIL import Image, ImageChops, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_compare(
    image_a: Path,
    image_b: Path,
    output: Literal["highlight_differences", "difference_map", "side_by_side"] = "highlight_differences",
) -> dict:
    """Compare two images pixel by pixel: how similar they are, the changed area, and a
    picture that highlights the differences (or a raw difference map, or the two side
    by side).
    """
    with Image.open(image_a) as a_src, Image.open(image_b) as b_src:
        a = ImageOps.exif_transpose(a_src).convert("RGB")
        b = ImageOps.exif_transpose(b_src).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    diff = ImageChops.difference(a, b)
    gray = ImageOps.grayscale(diff)
    histogram = gray.histogram()
    total = a.width * a.height
    changed = total - sum(histogram[:16])
    mean = sum(i * c for i, c in enumerate(histogram)) / total / 255

    if output == "difference_map":
        result = ImageOps.autocontrast(gray)
    elif output == "side_by_side":
        result = Image.new("RGB", (a.width * 2 + 10, a.height), "white")
        result.paste(a, (0, 0))
        result.paste(b, (a.width + 10, 0))
    else:
        mask = gray.point(lambda v: 255 if v > 16 else 0)
        overlay = Image.new("RGB", a.size, (255, 0, 0))
        result = Image.composite(overlay, a.convert("RGB"), mask.point(lambda v: 180 if v else 0))
    out = Path(f"{image_a.stem}_vs_{image_b.stem}_{output}.png")
    result.save(out)
    bbox = gray.point(lambda v: 255 if v > 16 else 0).getbbox()
    return {
        "file": out,
        "identical": changed == 0,
        "similarity_percent": round((1 - mean) * 100, 2),
        "changed_pixels_percent": round(changed / total * 100, 2),
        "changed_region_box": bbox,
        "sizes_matched": a.size == b.size,
    }
