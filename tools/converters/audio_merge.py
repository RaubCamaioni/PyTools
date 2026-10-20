# audio, merge, join, concatenate, mix

from pathlib import Path
from typing import Literal
from contextlib import closing
import numpy as np
import av


def audio_merge(
    first_audio: Path,
    second_audio: Path,
    mode: Literal["one_after_the_other", "mix_together"] = "one_after_the_other",
    gap_seconds: float = 0,
    output: Literal["mp3", "wav", "flac"] = "mp3",
) -> dict:
    """Join two audio files end to end (with an optional silent gap) or mix them so they
    play at the same time. The second file is resampled to match the first.
    """
    a, rate = _decode(first_audio)
    b, rate_b = _decode(second_audio)
    if a.size == 0 or b.size == 0:
        return {"error": "One of the files has no audio"}
    if rate_b != rate:
        idx = np.arange(0, len(b), rate_b / rate)
        b = np.stack([np.interp(idx, np.arange(len(b)), b[:, c]) for c in range(b.shape[1])], axis=1)
    channels = max(a.shape[1], b.shape[1])
    a = np.repeat(a, channels, axis=1) if a.shape[1] < channels else a[:, :channels]
    b = np.repeat(b, channels, axis=1) if b.shape[1] < channels else b[:, :channels]
    if mode == "mix_together":
        length = max(len(a), len(b))
        mixed = np.zeros((length, channels))
        mixed[: len(a)] += a
        mixed[: len(b)] += b
        peak = np.abs(mixed).max()
        samples = mixed / peak * 0.98 if peak > 1 else mixed
    else:
        gap = np.zeros((int(max(0.0, gap_seconds) * rate), channels))
        samples = np.concatenate([a, gap, b])
    out = Path(f"{first_audio.stem}_{mode}.{output}")
    _encode(out, np.clip(samples, -1, 1), rate, output)
    return {"file": out, "duration_seconds": round(len(samples) / rate, 2), "sample_rate": rate, "channels": channels}


def _decode(path: Path) -> tuple[np.ndarray, int]:
    chunks, rate = [], 44100
    with closing(av.open(str(path))) as container:
        stream = container.streams.audio[0]
        rate = stream.rate
        resampler = av.AudioResampler(format="fltp", layout=stream.layout.name, rate=rate)
        for frame in container.decode(stream):
            for f in resampler.resample(frame):
                chunks.append(f.to_ndarray().T)
    return (np.concatenate(chunks).astype(np.float64) if chunks else np.zeros((0, 1))), rate


def _encode(path: Path, samples: np.ndarray, rate: int, fmt: str) -> None:
    codec = {"mp3": "mp3", "wav": "pcm_s16le", "flac": "flac"}[fmt]
    layout = "mono" if samples.shape[1] == 1 else "stereo"
    with closing(av.open(str(path), mode="w")) as container:
        stream = container.add_stream(codec, rate=rate, layout=layout)
        for start in range(0, len(samples), 4096):
            block = np.ascontiguousarray(samples[start : start + 4096].T.astype(np.float32))
            frame = av.AudioFrame.from_ndarray(block, format="fltp", layout=layout)
            frame.sample_rate = rate
            frame.pts = None
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
