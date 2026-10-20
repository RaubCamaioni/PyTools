# image, collage, grid, combine, montage

from pathlib import Path
from typing import Literal
import math
import re
import tempfile
import zipfile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic", ".heif"}


def image_collage(
    images_zip: Path,
    layout: Literal["grid", "horizontal_strip", "vertical_strip"] = "grid",
    cell_size: int = 400,
    gap: int = 8,
    background: Literal["white", "black"] = "white",
) -> dict:
    """Combine the images in a zip into one picture: a grid (ordered by file name), a
    horizontal strip or a vertical strip. Each image is fitted into a square cell of
    the given size.
    """
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        work = Path(tmp)
        if zipfile.is_zipfile(images_zip):
            with zipfile.ZipFile(images_zip) as zf:
                for member in zf.infolist():
                    if (
                        not member.is_dir()
                        and Path(member.filename).suffix.lower() in IMAGE_EXT
                        and "__MACOSX" not in member.filename
                    ):
                        (work / Path(member.filename).name).write_bytes(zf.read(member))
        else:
            (work / images_zip.name).write_bytes(images_zip.read_bytes())
        files = sorted(
            (p for p in work.iterdir() if p.suffix.lower() in IMAGE_EXT),
            key=lambda p: [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", p.name)],
        )[:100]
        if not files:
            return {"error": "No images found in the zip"}
        cell = max(50, min(cell_size, 1200))
        gap = max(0, min(gap, 100))
        tiles = []
        for p in files:
            with Image.open(p) as img:
                tiles.append(ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (cell, cell), Image.LANCZOS))

    n = len(tiles)
    cols = n if layout == "horizontal_strip" else 1 if layout == "vertical_strip" else math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * cell + (cols + 1) * gap, rows * cell + (rows + 1) * gap), background)
    for i, tile in enumerate(tiles):
        x = gap + (i % cols) * (cell + gap)
        y = gap + (i // cols) * (cell + gap)
        sheet.paste(tile, (x, y))
    out = Path(f"{images_zip.stem}_collage.jpg")
    sheet.save(out, quality=90)
    return {"file": out, "images": n, "grid": f"{cols}x{rows}", "size": f"{sheet.width}x{sheet.height}"}
