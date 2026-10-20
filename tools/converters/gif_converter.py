# gif, mp4, webp, apng, animation, frames, converter

from pathlib import Path
from typing import Literal
import zipfile
from fractions import Fraction
from PIL import Image, ImageSequence
import av


def _frames(image: Path):
    with Image.open(image) as img:
        default = int(img.info.get("duration", 100)) or 100
        for frame in ImageSequence.Iterator(img):
            yield frame.convert("RGBA"), int(frame.info.get("duration", default)) or default


def gif_converter(
    animation: Path,
    output: Literal["mp4", "webm", "webp", "apng", "png_frames_zip", "sprite_sheet"] = "mp4",
) -> Path:
    """Convert an animated GIF (or animated WebP/APNG) to MP4, WebM, animated WebP, APNG, a zip of PNG frames or a
    horizontal sprite sheet.
    """
    frames = list(_frames(animation))
    if not frames:
        raise ValueError("No frames found")
    w, h = frames[0][0].size

    if output in ("mp4", "webm"):
        out = animation.with_suffix("." + output)
        avg_ms = max(10, sum(d for _, d in frames) / len(frames))
        fps = max(1, min(60, round(1000 / avg_ms)))
        with av.open(str(out), mode="w") as container:
            codec = "libvpx-vp9" if output == "webm" else "libx264"
            stream = container.add_stream(codec, rate=fps)
            stream.width, stream.height = max(2, w - (w % 2)), max(2, h - (h % 2))
            time_base = Fraction(1, fps)
            stream.codec_context.time_base = time_base
            stream.pix_fmt = "yuv420p" if output == "mp4" else "yuv420p"
            if output == "mp4":
                stream.options = {"crf": "23", "preset": "veryfast"}
            else:
                stream.options = {"crf": "32", "b:v": "0", "cpu-used": "5", "row-mt": "1"}
            background = Image.new("RGB", (stream.width, stream.height), "white")
            index = 0
            for frame, duration in frames:
                rgb = background.copy()
                rgb.paste(
                    frame.resize((stream.width, stream.height)),
                    mask=frame.resize((stream.width, stream.height)).getchannel("A"),
                )
                repeat = max(1, round(duration / (1000 / fps)))
                for _ in range(repeat):
                    video_frame = av.VideoFrame.from_image(rgb)
                    video_frame.pts = index
                    video_frame.time_base = time_base
                    index += 1
                    for packet in stream.encode(video_frame):
                        container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        return out

    if output in ("webp", "apng"):
        out = animation.with_suffix(".webp" if output == "webp" else ".png")
        first = frames[0][0]
        first.save(
            out,
            "WEBP" if output == "webp" else "PNG",
            save_all=True,
            append_images=[f for f, _ in frames[1:]],
            duration=[d for _, d in frames],
            loop=0,
            lossless=False,
            quality=85,
        )
        return out

    if output == "sprite_sheet":
        cols = len(frames)
        sheet = Image.new("RGBA", (w * cols, h), (0, 0, 0, 0))
        for i, (frame, _) in enumerate(frames):
            sheet.paste(frame, (i * w, 0))
        out = animation.with_name(f"{animation.stem}_sprite_{cols}x1_{w}x{h}.png")
        sheet.save(out, "PNG", optimize=True)
        return out

    out = animation.with_name(f"{animation.stem}_frames.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        for i, (frame, duration) in enumerate(frames, 1):
            tmp = Path(f"frame_{i:04d}_{duration}ms.png")
            frame.save(tmp, "PNG")
            zf.write(tmp)
            tmp.unlink()
    return out
