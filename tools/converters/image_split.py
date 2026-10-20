# image, split, tiles, grid, instagram

from pathlib import Path
import zipfile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def image_split(image: Path, columns: int = 3, rows: int = 3) -> dict:
    """Cut an image into a grid of equal tiles (3x3 for an Instagram grid, 2x1 for a
    banner...), numbered left to right, top to bottom, zipped.
    """
    columns, rows = max(1, min(columns, 20)), max(1, min(rows, 20))
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    tile_w, tile_h = img.width // columns, img.height // rows
    if tile_w < 1 or tile_h < 1:
        return {"error": "The image is too small for that many tiles"}
    out = image.with_name(f"{image.stem}_{columns}x{rows}_tiles.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        n = 0
        for r in range(rows):
            for c in range(columns):
                n += 1
                tile = img.crop((c * tile_w, r * tile_h, (c + 1) * tile_w, (r + 1) * tile_h))
                tmp = Path(f"{image.stem}_tile_{n:02d}_r{r + 1}c{c + 1}.jpg")
                tile.save(tmp, quality=92)
                zf.write(tmp)
                tmp.unlink()
    return {"file": out, "tiles": columns * rows, "tile_size": f"{tile_w}x{tile_h}"}
