# audio, trim, cut, clip, mp3, wav

from pathlib import Path
from typing import Literal
from contextlib import ExitStack, closing
import av


def audio_trim(
    audio: Path,
    start_seconds: float = 0,
    end_seconds: float = 30,
    output: Literal["same_as_input", "mp3", "wav", "aac", "ogg", "flac"] = "same_as_input",
) -> Path:
    """Cut a section out of an audio file (or the audio track of a video) between two
    times, optionally converting the format.
    """
    codecs = {
        "mp3": "mp3",
        "wav": "pcm_s16le",
        "aac": "aac",
        "ogg": "libopus",
        "flac": "flac",
        "m4a": "aac",
        "opus": "libopus",
    }
    ext = audio.suffix.lstrip(".").lower() if output == "same_as_input" else output
    if ext not in codecs:
        ext = "mp3"
    out = audio.with_name(f"{audio.stem}_trim.{ext}")
    start = max(0.0, start_seconds)
    end = max(start + 0.1, end_seconds)

    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(audio))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_stream = src.streams.audio[0]
        rate = 48000 if codecs[ext] == "libopus" else in_stream.rate
        out_stream = dst.add_stream(codecs[ext], rate=rate)
        if codecs[ext] in ("mp3", "aac", "libopus"):
            out_stream.bit_rate = 128_000
        if start > 0:
            src.seek(int(start * av.time_base), backward=True, any_frame=False)
        for frame in src.decode(in_stream):
            t = float(frame.pts * in_stream.time_base) if frame.pts is not None else 0.0
            if t < start:
                continue
            if t > end:
                break
            frame.pts = None
            for packet in out_stream.encode(frame):
                dst.mux(packet)
        for packet in out_stream.encode(None):
            dst.mux(packet)
    return out
