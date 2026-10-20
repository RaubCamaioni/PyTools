# gif, animation, images, slideshow, maker

from pathlib import Path
from typing import Literal
import re
import tempfile
import zipfile
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic", ".heif"}


def gif_from_images(
    images_zip: Path,
    frame_milliseconds: int = 500,
    width: int = 480,
    loop: Literal["forever", "once"] = "forever",
    output: Literal["gif", "webp", "apng", "mp4"] = "gif",
) -> dict:
    """Turn a zip of images (ordered by file name) into an animated GIF, WebP, APNG or
    MP4 slideshow, every frame resized to the same width.
    """
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        work = Path(tmp)
        with zipfile.ZipFile(images_zip) as zf:
            for member in zf.infolist():
                if (
                    not member.is_dir()
                    and Path(member.filename).suffix.lower() in IMAGE_EXT
                    and "__MACOSX" not in member.filename
                ):
                    (work / Path(member.filename).name).write_bytes(zf.read(member))
        files = sorted(
            (p for p in work.iterdir() if p.suffix.lower() in IMAGE_EXT),
            key=lambda p: [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", p.name)],
        )[:300]
        if not files:
            return {"error": "No images found in the zip"}
        width = max(16, min(width, 1920))
        frames = []
        for p in files:
            with Image.open(p) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                height = max(1, round(img.height * width / img.width))
                frames.append(img.resize((width, height), Image.LANCZOS))
    height = max(f.height for f in frames)
    frames = [ImageOps.pad(f, (width, height), color="black") for f in frames]
    delay = max(20, min(frame_milliseconds, 10000))
    loops = 0 if loop == "forever" else 1

    if output == "mp4":
        import av
        from fractions import Fraction

        out = images_zip.with_name(f"{images_zip.stem}_slideshow.mp4")
        fps = 10
        with av.open(str(out), mode="w") as container:
            stream = container.add_stream("libx264", rate=fps)
            stream.width, stream.height = width - width % 2, height - height % 2
            stream.pix_fmt = "yuv420p"
            stream.codec_context.time_base = Fraction(1, fps)
            n = 0
            for frame in frames:
                for _ in range(max(1, round(delay / 100))):
                    vf = av.VideoFrame.from_image(frame.resize((stream.width, stream.height)))
                    vf.pts, vf.time_base = n, Fraction(1, fps)
                    n += 1
                    for packet in stream.encode(vf):
                        container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
    else:
        ext = {"gif": "gif", "webp": "webp", "apng": "png"}[output]
        out = images_zip.with_name(f"{images_zip.stem}_slideshow.{ext}")
        if output == "gif":
            frames = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT) for f in frames]
        frames[0].save(
            out, save_all=True, append_images=frames[1:], duration=delay, loop=loops, optimize=output == "gif"
        )
    return {"file": out, "frames": len(frames), "size": f"{width}x{height}"}
