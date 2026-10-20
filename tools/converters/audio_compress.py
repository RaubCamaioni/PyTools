# audio, compress, bitrate, mp3, smaller, converter

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
import av


def audio_compress(
    audio: Path,
    bitrate: Literal["64k", "96k", "128k", "192k", "320k"] = "96k",
    output: Literal["mp3", "aac", "opus"] = "mp3",
    mono: Literal["no", "yes"] = "no",
) -> dict:
    """Shrink an audio file by re-encoding it at a lower bitrate (and optionally to
    mono): podcasts and voice memos go to 64k, music to 128k or higher. Reports the
    size change.
    """
    codec = {"mp3": "mp3", "aac": "aac", "opus": "libopus"}[output]
    ext = {"mp3": "mp3", "aac": "m4a", "opus": "opus"}[output]
    out = audio.with_name(f"{audio.stem}_{bitrate}.{ext}")
    before = audio.stat().st_size
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(audio))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_a = src.streams.audio[0]
        rate = 48000 if codec == "libopus" else in_a.rate
        layout = "mono" if mono == "yes" else ("stereo" if in_a.channels >= 2 else "mono")
        out_a = dst.add_stream(codec, rate=rate, layout=layout)
        out_a.bit_rate = int(bitrate[:-1]) * 1000
        resampler = av.AudioResampler(format="fltp" if codec != "libopus" else "flt", layout=layout, rate=rate)
        for frame in src.decode(in_a):
            for rf in resampler.resample(frame):
                rf.pts = None
                for p in out_a.encode(rf):
                    dst.mux(p)
        for p in out_a.encode(None):
            dst.mux(p)
    after = out.stat().st_size
    return {
        "file": out,
        "before_bytes": before,
        "after_bytes": after,
        "saved": f"{(1 - after / before) * 100:.1f}%" if before else "n/a",
    }
