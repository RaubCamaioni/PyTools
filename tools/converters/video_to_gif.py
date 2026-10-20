# video, gif, mp4, animation, converter

from pathlib import Path
from contextlib import closing
from PIL import Image
import av


def video_to_gif(
    video: Path,
    start_seconds: float = 0,
    duration_seconds: float = 5,
    fps: int = 10,
    width: int = 480,
) -> Path:
    """Turn a clip of a video (MP4, MOV, WEBM, AVI...) into an animated GIF: choose
    start time, length (max 15 s), frame rate and width.
    """
    fps = max(1, min(fps, 30))
    duration = max(0.1, min(duration_seconds, 15))
    width = max(32, min(width, 800))
    frames: list[Image.Image] = []
    with closing(av.open(str(video))) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        if start_seconds > 0:
            container.seek(int(start_seconds * av.time_base), backward=True, any_frame=False)
        next_time = start_seconds
        step = 1 / fps
        for frame in container.decode(stream):
            t = float(frame.pts * stream.time_base) if frame.pts is not None else next_time
            if t < next_time - 1e-6:
                continue
            if t > start_seconds + duration:
                break
            img = frame.to_image()
            height = max(1, round(img.height * width / img.width))
            frames.append(img.resize((width, height), Image.LANCZOS))
            next_time += step
            if len(frames) >= fps * 15:
                break
    if not frames:
        raise ValueError("No frames found in that time range")

    out = video.with_name(f"{video.stem}.gif")
    first = frames[0].convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    rest = [f.convert("RGB").quantize(palette=first, dither=Image.Dither.FLOYDSTEINBERG) for f in frames[1:]]
    first.save(out, save_all=True, append_images=rest, duration=int(1000 / fps), loop=0, optimize=False, disposal=2)
    return out
