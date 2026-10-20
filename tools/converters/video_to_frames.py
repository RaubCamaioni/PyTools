# video, frames, image, screenshot, thumbnail

from pathlib import Path
from typing import Literal
from contextlib import closing
import zipfile
import av


def video_to_frames(
    video: Path,
    mode: Literal["single_frame", "every_n_seconds", "contact_sheet"] = "single_frame",
    at_seconds: float = 1,
    max_frames: int = 20,
) -> Path:
    """Grab a still from a video at a time, extract frames every N seconds (zip of JPGs), or build a contact sheet
    thumbnail grid.
    """
    max_frames = max(1, min(max_frames, 60))
    captured = []
    with closing(av.open(str(video))) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        total = float(stream.duration * stream.time_base) if stream.duration else None

        if mode == "single_frame":
            container.seek(int(max(0, at_seconds) * av.time_base), backward=True, any_frame=False)
            last = None
            for frame in container.decode(stream):
                t = float(frame.pts * stream.time_base) if frame.pts is not None else 0
                last = (t, frame)
                if t >= at_seconds - 1e-3:
                    captured.append((t, frame.to_image()))
                    break
            if not captured and last is not None:  # time is past the end: use the last frame
                captured.append((last[0], last[1].to_image()))
            if not captured:
                raise ValueError("Could not decode a frame at that time")
            out = video.with_name(f"{video.stem}_{captured[0][0]:.2f}s.jpg")
            captured[0][1].convert("RGB").save(out, quality=92)
            return out

        if mode == "contact_sheet":
            interval = (total or 60) / max_frames
        else:
            interval = max(0.1, at_seconds)
        next_time = 0.0
        for frame in container.decode(stream):
            t = float(frame.pts * stream.time_base) if frame.pts is not None else next_time
            if t + 1e-6 < next_time:
                continue
            captured.append((t, frame.to_image()))
            next_time += interval
            if len(captured) >= max_frames:
                break

    if not captured:
        raise ValueError("No frames decoded")

    if mode == "contact_sheet":
        from PIL import Image, ImageDraw

        cols = 4 if len(captured) > 4 else len(captured)
        rows = -(-len(captured) // cols)
        tw = 320
        th = round(captured[0][1].height * tw / captured[0][1].width)
        sheet = Image.new("RGB", (cols * tw, rows * (th + 18)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (t, img) in enumerate(captured):
            x, y = (i % cols) * tw, (i // cols) * (th + 18)
            sheet.paste(img.convert("RGB").resize((tw, th)), (x, y))
            draw.text((x + 4, y + th + 2), f"{t:.1f}s", fill="black")
        out = video.with_name(f"{video.stem}_contact_sheet.jpg")
        sheet.save(out, quality=88)
        return out

    out = video.with_name(f"{video.stem}_frames.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        for i, (t, img) in enumerate(captured, 1):
            tmp = Path(f"frame_{i:03d}_{t:.2f}s.jpg")
            img.convert("RGB").save(tmp, quality=90)
            zf.write(tmp)
            tmp.unlink()
    return out
