# video, trim, cut, clip, mp4

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
from fractions import Fraction
import av


def video_trim(
    video: Path,
    start_seconds: float = 0,
    end_seconds: float = 10,
    rotate: Literal["none", "90_clockwise", "90_counterclockwise", "180"] = "none",
    audio: Literal["keep", "remove"] = "keep",
) -> Path:
    """Cut a clip out of a video between two times (max 60 s), optionally rotating it and dropping the sound. Output is
    MP4 (H.264/AAC).
    """
    start = max(0.0, start_seconds)
    end = min(max(start + 0.2, end_seconds), start + 60)
    out = video.with_name(f"{video.stem}_{start:g}s_{end:g}s.mp4")
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(video))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_v = src.streams.video[0]
        in_v.thread_type = "AUTO"
        in_a = src.streams.audio[0] if (audio == "keep" and src.streams.audio) else None
        w, h = in_v.codec_context.width, in_v.codec_context.height
        if rotate in ("90_clockwise", "90_counterclockwise"):
            w, h = h, w
        w, h = max(2, w // 2 * 2), max(2, h // 2 * 2)
        fps = min(60, float(in_v.average_rate or 30))
        out_v = dst.add_stream("libx264", rate=round(fps))
        out_v.width, out_v.height, out_v.pix_fmt = w, h, "yuv420p"
        time_base = Fraction(1, round(fps))
        out_v.codec_context.time_base = time_base
        out_v.options = {"crf": "22", "preset": "veryfast"}
        out_a = dst.add_stream("aac", rate=in_a.rate) if in_a is not None else None
        if out_a is not None:
            out_a.bit_rate = 128_000

        src.seek(int(start * av.time_base), backward=True, any_frame=False)
        video_done = False
        audio_done = in_a is None
        frames_written = 0
        for packet in src.demux([s for s in (in_v, in_a) if s is not None]):
            # packets without dts are flush packets; decoding them releases the delayed frames
            is_video = packet.stream.type == "video"
            if (is_video and video_done) or (not is_video and audio_done):
                if video_done and audio_done:
                    break
                continue
            for frame in packet.decode():
                t = float(frame.pts * packet.stream.time_base) if frame.pts is not None else start
                if t < start:
                    continue
                if t > end:
                    if is_video:
                        video_done = True
                    else:
                        audio_done = True
                    break
                frame.pts = None
                if is_video:
                    if rotate != "none":
                        from PIL import Image

                        img = frame.to_image()
                        img = img.transpose(
                            {
                                "90_clockwise": Image.Transpose.ROTATE_270,
                                "90_counterclockwise": Image.Transpose.ROTATE_90,
                                "180": Image.Transpose.ROTATE_180,
                            }[rotate]
                        )
                        frame = av.VideoFrame.from_image(img.resize((w, h)))
                    frame = frame.reformat(width=w, height=h, format="yuv420p")
                    frame.pts = frames_written
                    frame.time_base = time_base
                    frames_written += 1
                    for p in out_v.encode(frame):
                        dst.mux(p)
                elif out_a is not None:
                    for p in out_a.encode(frame):
                        dst.mux(p)
        for p in out_v.encode():
            dst.mux(p)
        if out_a is not None:
            for p in out_a.encode():
                dst.mux(p)
    return out
