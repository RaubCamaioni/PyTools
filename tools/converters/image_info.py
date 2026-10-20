# image, exif, metadata, info, inspect

from pathlib import Path
from PIL import Image, ExifTags
import pillow_heif

pillow_heif.register_heif_opener()


def image_info(image: Path) -> dict:
    """Show an image's format, dimensions, colour mode, DPI, file size and EXIF metadata
    (camera, date, GPS, orientation).
    """
    with Image.open(image) as img:
        info = {
            "file": image.name,
            "file_size_bytes": image.stat().st_size,
            "format": img.format,
            "width": img.width,
            "height": img.height,
            "megapixels": round(img.width * img.height / 1e6, 2),
            "aspect_ratio": round(img.width / img.height, 4) if img.height else None,
            "mode": img.mode,
            "bands": img.getbands(),
            "has_transparency": "A" in img.getbands() or "transparency" in img.info,
            "dpi": img.info.get("dpi"),
            "animated_frames": getattr(img, "n_frames", 1),
        }
        exif = {}
        try:
            raw = img.getexif()
            for tag, value in raw.items():
                name = ExifTags.TAGS.get(tag, str(tag))
                if isinstance(value, bytes):
                    value = f"<{len(value)} bytes>"
                exif[name] = str(value)[:200]
            gps = raw.get_ifd(ExifTags.IFD.GPSInfo)
            if gps:
                exif["GPS"] = {ExifTags.GPSTAGS.get(k, str(k)): str(v) for k, v in gps.items()}
            detail = raw.get_ifd(ExifTags.IFD.Exif)
            for tag, value in detail.items():
                name = ExifTags.TAGS.get(tag, str(tag))
                if name in (
                    "DateTimeOriginal",
                    "ExposureTime",
                    "FNumber",
                    "ISOSpeedRatings",
                    "FocalLength",
                    "LensModel",
                    "ExposureBiasValue",
                ):
                    exif[name] = str(value)
        except Exception:  # noqa: BLE001 - metadata is best effort
            pass
        info["exif"] = exif or "none"
    return info
