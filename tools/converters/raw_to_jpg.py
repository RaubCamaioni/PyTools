# image, raw, camera, cr2, nef, arw, dng, jpg, converter

from pathlib import Path
from typing import Literal
import rawpy
from PIL import Image


def raw_to_jpg(
    raw_photo: Path,
    output: Literal["jpg", "png", "tiff"] = "jpg",
    white_balance: Literal["camera", "auto"] = "camera",
    brightness: float = 1.0,
    max_dimension: int = 0,
) -> dict:
    """Develop a camera RAW file (CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2, PEF...) into a JPG, PNG or TIFF, with camera or automatic white balance and a brightness multiplier."""
    with rawpy.imread(str(raw_photo)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=white_balance == "camera",
            use_auto_wb=white_balance == "auto",
            bright=max(0.1, min(brightness, 5.0)),
            no_auto_bright=False,
            output_bps=8,
        )
        sizes = raw.sizes
    img = Image.fromarray(rgb)
    if max_dimension > 0:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    out = raw_photo.with_name(f"{raw_photo.stem}.{output}")
    if output == "jpg":
        img.save(out, "JPEG", quality=92, optimize=True)
    elif output == "png":
        img.save(out, "PNG", optimize=True)
    else:
        img.save(out, "TIFF")
    return {"file": out, "sensor_size": f"{sizes.raw_width}x{sizes.raw_height}", "output_size": f"{img.width}x{img.height}"}
