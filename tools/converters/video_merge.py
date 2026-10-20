# video, merge, join, concatenate, combine

from pathlib import Path
from contextlib import ExitStack, closing
from fractions import Fraction
import av

MAX_SECONDS_EACH = 60


def video_merge(first_video: Path, second_video: Path, max_height: int = 720) -> dict:
    """Join two videos one after the other into a single MP4 (both re-encoded to the
    same size and frame rate; sound kept). Each clip is cut at 60 seconds to fit the
    time limit.
    """
    out = Path(f"{first_video.stem}_plus_{second_video.stem}.mp4")
    with ExitStack() as stack:
        srcs = [stack.enter_context(closing(av.open(str(p)))) for p in (first_video, second_video)]
        first_v = srcs[0].streams.video[0]
        scale = min(1.0, max(144, max_height) / first_v.codec_context.height)
        w = max(2, int(first_v.codec_context.width * scale) // 2 * 2)
        h = max(2, int(first_v.codec_context.height * scale) // 2 * 2)
        fps = min(30, float(first_v.average_rate or 30))
        has_audio = all(s.streams.audio for s in srcs)
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        out_v = dst.add_stream("libx264", rate=round(fps))
        out_v.width, out_v.height, out_v.pix_fmt = w, h, "yuv420p"
        time_base = Fraction(1, round(fps))
        out_v.codec_context.time_base = time_base
        out_v.options = {"crf": "23", "preset": "veryfast"}
        out_a = dst.add_stream("aac", rate=48000) if has_audio else None
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=48000) if has_audio else None
        frames = 0
        for src in srcs:
            in_v = src.streams.video[0]
            in_v.thread_type = "AUTO"
            in_a = src.streams.audio[0] if has_audio else None
            for packet in src.demux([s for s in (in_v, in_a) if s is not None]):
                t = float(packet.pts * packet.stream.time_base) if packet.pts is not None else 0.0
                if t > MAX_SECONDS_EACH:
                    continue
                if packet.stream.type == "video":
                    for frame in packet.decode():
                        vf = frame.reformat(width=w, height=h, format="yuv420p")
                        vf.pts, vf.time_base = frames, time_base
                        frames += 1
                        for p in out_v.encode(vf):
                            dst.mux(p)
                elif out_a is not None:
                    for frame in packet.decode():
                        for rf in resampler.resample(frame):
                            rf.pts = None
                            for p in out_a.encode(rf):
                                dst.mux(p)
        for p in out_v.encode():
            dst.mux(p)
        if out_a is not None:
            for p in out_a.encode():
                dst.mux(p)
    return {
        "file": out,
        "frames": frames,
        "resolution": f"{w}x{h}",
        "sound": "kept" if has_audio else "none in one of the clips",
    }
