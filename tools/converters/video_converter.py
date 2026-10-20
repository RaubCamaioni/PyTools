# video, mp4, webm, mov, mkv, compress, resize, converter

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
from fractions import Fraction
import av

MAX_SECONDS = 120


def video_converter(
    video: Path,
    output: Literal["mp4", "webm", "mov", "mkv"] = "mp4",
    max_height: int = 720,
    quality: Literal["medium", "small_file", "high"] = "medium",
    audio: Literal["keep", "remove"] = "keep",
) -> dict:
    """Convert and compress a video (MP4, MOV, MKV, WEBM, AVI, 3GP...): choose the
    container, cap the resolution and pick a quality. Clips longer than 2 minutes are
    cut at 2 minutes to fit the sandbox time limit.
    """
    crf = {"small_file": 30, "medium": 25, "high": 20}[quality]
    out = video.with_name(f"{video.stem}_{max_height}p.{output}")
    frames_written = 0
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(video))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_v = src.streams.video[0]
        in_v.thread_type = "AUTO"
        in_a = src.streams.audio[0] if (audio == "keep" and src.streams.audio) else None

        scale = min(1.0, max(144, max_height) / in_v.codec_context.height)
        width = max(2, int(in_v.codec_context.width * scale) // 2 * 2)
        height = max(2, int(in_v.codec_context.height * scale) // 2 * 2)
        fps = min(30, float(in_v.average_rate or 30))

        vcodec = "libvpx-vp9" if output == "webm" else "libx264"
        out_v = dst.add_stream(vcodec, rate=round(fps))
        out_v.width, out_v.height, out_v.pix_fmt = width, height, "yuv420p"
        time_base = Fraction(1, round(fps))
        out_v.codec_context.time_base = time_base
        out_v.options = (
            {"crf": str(crf + 6), "b:v": "0", "cpu-used": "6", "row-mt": "1", "deadline": "realtime"}
            if output == "webm"
            else {"crf": str(crf), "preset": "veryfast"}
        )
        out_a = None
        if in_a is not None:
            acodec = "libopus" if output == "webm" else "aac"
            out_a = dst.add_stream(acodec, rate=48000 if acodec == "libopus" else in_a.rate)
            out_a.bit_rate = 96_000

        limit = MAX_SECONDS
        for packet in src.demux([s for s in (in_v, in_a) if s is not None]):
            # a packet without dts is the demuxer's flush packet: decoding it releases
            # the delayed frames
            t = float(packet.pts * packet.stream.time_base) if packet.pts is not None else 0.0
            if t > limit:
                continue
            if packet.stream.type == "video":
                for frame in packet.decode():
                    frame = frame.reformat(width=width, height=height, format="yuv420p")
                    frame.pts = frames_written
                    frame.time_base = time_base
                    frames_written += 1
                    for p in out_v.encode(frame):
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
    return {
        "file": out,
        "resolution": f"{width}x{height}",
        "frames": frames_written,
        "before_bytes": video.stat().st_size,
        "after_bytes": out.stat().st_size,
    }
