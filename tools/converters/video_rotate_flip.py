# video, rotate, flip, mirror, orientation

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
from fractions import Fraction
import av
from PIL import Image

MAX_SECONDS = 90


def video_rotate_flip(
    video: Path,
    operation: Literal[
        "rotate_90_clockwise", "rotate_90_counterclockwise", "rotate_180", "flip_horizontal", "flip_vertical"
    ] = "rotate_90_clockwise",
    audio: Literal["keep", "remove"] = "keep",
) -> dict:
    """Rotate or mirror a video (phone clips recorded sideways), re-encoded as MP4.
    Clips are cut at 90 seconds to fit the sandbox time limit.
    """
    transpose = {
        "rotate_90_clockwise": Image.Transpose.ROTATE_270,
        "rotate_90_counterclockwise": Image.Transpose.ROTATE_90,
        "rotate_180": Image.Transpose.ROTATE_180,
        "flip_horizontal": Image.Transpose.FLIP_LEFT_RIGHT,
        "flip_vertical": Image.Transpose.FLIP_TOP_BOTTOM,
    }[operation]
    out = video.with_name(f"{video.stem}_{operation}.mp4")
    frames = 0
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(video))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_v = src.streams.video[0]
        in_v.thread_type = "AUTO"
        in_a = src.streams.audio[0] if (audio == "keep" and src.streams.audio) else None
        w, h = in_v.codec_context.width, in_v.codec_context.height
        if operation.startswith("rotate_90"):
            w, h = h, w
        w, h = max(2, w // 2 * 2), max(2, h // 2 * 2)
        fps = min(30, float(in_v.average_rate or 30))
        out_v = dst.add_stream("libx264", rate=round(fps))
        out_v.width, out_v.height, out_v.pix_fmt = w, h, "yuv420p"
        time_base = Fraction(1, round(fps))
        out_v.codec_context.time_base = time_base
        out_v.options = {"crf": "23", "preset": "veryfast"}
        out_a = dst.add_stream("aac", rate=in_a.rate) if in_a is not None else None
        for packet in src.demux([s for s in (in_v, in_a) if s is not None]):
            t = float(packet.pts * packet.stream.time_base) if packet.pts is not None else 0.0
            if t > MAX_SECONDS:
                continue
            if packet.stream.type == "video":
                for frame in packet.decode():
                    img = frame.to_image().transpose(transpose).resize((w, h))
                    vf = av.VideoFrame.from_image(img).reformat(format="yuv420p")
                    vf.pts, vf.time_base = frames, time_base
                    frames += 1
                    for p in out_v.encode(vf):
                        dst.mux(p)
            elif out_a is not None:
                for frame in packet.decode():
                    frame.pts = None
                    for p in out_a.encode(frame):
                        dst.mux(p)
        for p in out_v.encode():
            dst.mux(p)
        if out_a is not None:
            for p in out_a.encode():
                dst.mux(p)
    return {"file": out, "frames": frames, "resolution": f"{w}x{h}"}
