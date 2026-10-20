# video, speed, slow motion, timelapse, reverse

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
from fractions import Fraction
import av

MAX_FRAMES = 2400


def video_speed(
    video: Path,
    speed: Literal["0.25x", "0.5x", "2x", "4x", "8x", "reverse"] = "2x",
) -> dict:
    """Speed a video up (time-lapse), slow it down, or play it backwards. The sound is
    dropped (it would be unintelligible); output is a silent MP4. Long clips are cut
    to fit the time limit.
    """
    out = video.with_name(f"{video.stem}_{speed.replace('.', '_')}.mp4")
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(video))))
        in_v = src.streams.video[0]
        in_v.thread_type = "AUTO"
        w, h = max(2, in_v.codec_context.width // 2 * 2), max(2, in_v.codec_context.height // 2 * 2)
        fps = min(30, float(in_v.average_rate or 30))
        factor = {"0.25x": 0.25, "0.5x": 0.5, "2x": 2, "4x": 4, "8x": 8, "reverse": 1}[speed]
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        out_v = dst.add_stream("libx264", rate=round(fps))
        out_v.width, out_v.height, out_v.pix_fmt = w, h, "yuv420p"
        time_base = Fraction(1, round(fps))
        out_v.codec_context.time_base = time_base
        out_v.options = {"crf": "23", "preset": "veryfast"}

        def emit(frame, index):
            vf = frame.reformat(width=w, height=h, format="yuv420p")
            vf.pts, vf.time_base = index, time_base
            for p in out_v.encode(vf):
                dst.mux(p)

        written = 0
        if speed == "reverse":
            images = []
            for frame in src.decode(in_v):
                images.append(frame.to_image())
                if len(images) >= min(MAX_FRAMES, 450):
                    break
            for img in reversed(images):
                emit(av.VideoFrame.from_image(img), written)
                written += 1
        else:
            index, carry = 0, 0.0
            for frame in src.decode(in_v):
                carry += 1 / factor
                while carry >= 1 and written < MAX_FRAMES:
                    emit(frame, written)
                    written += 1
                    carry -= 1
                index += 1
                if written >= MAX_FRAMES:
                    break
        for p in out_v.encode():
            dst.mux(p)
    return {"file": out, "frames": written, "duration_seconds": round(written / fps, 2)}
