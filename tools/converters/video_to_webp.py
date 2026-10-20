# video, webp, animated, sticker, converter

from pathlib import Path
from contextlib import closing
from PIL import Image
import av


def video_to_webp(
    video: Path, start_seconds: float = 0, duration_seconds: float = 5, fps: int = 12, width: int = 480
) -> dict:
    """Turn a clip of a video into an animated WebP (smaller and sharper than a GIF;
    what messaging stickers use). Pick the start, length (max 15 s), frame rate and
    width.
    """
    fps = max(1, min(fps, 30))
    duration = max(0.1, min(duration_seconds, 15))
    width = max(32, min(width, 1024))
    frames = []
    with closing(av.open(str(video))) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        if start_seconds > 0:
            container.seek(int(start_seconds * av.time_base), backward=True, any_frame=False)
        next_time, step = start_seconds, 1 / fps
        for frame in container.decode(stream):
            t = float(frame.pts * stream.time_base) if frame.pts is not None else next_time
            if t < next_time - 1e-6:
                continue
            if t > start_seconds + duration:
                break
            img = frame.to_image()
            frames.append(img.resize((width, max(1, round(img.height * width / img.width))), Image.LANCZOS))
            next_time += step
    if not frames:
        return {"error": "No frames in that time range"}
    out = video.with_name(f"{video.stem}.webp")
    frames[0].save(
        out, "WEBP", save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, quality=80, method=4
    )
    return {"file": out, "frames": len(frames), "bytes": out.stat().st_size}
