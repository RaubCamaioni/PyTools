# audio, volume, fade, normalize, speed, mono, resample

from pathlib import Path
from typing import Literal
from contextlib import closing
import numpy as np
import av


def audio_adjust(
    audio: Path,
    volume_percent: int = 100,
    fade_in_seconds: float = 0,
    fade_out_seconds: float = 0,
    speed_percent: int = 100,
    normalize: Literal["no", "yes"] = "no",
    channels: Literal["keep", "mono", "stereo"] = "keep",
    output: Literal["mp3", "wav", "flac", "ogg"] = "mp3",
) -> dict:
    """Change an audio file's volume, add fades, speed it up or slow it down (pitch
    follows), normalise the peak to full scale, and convert to mono or stereo, then
    save as MP3/WAV/FLAC/OGG.
    """
    samples, rate = _decode(audio)
    if samples.size == 0:
        return {"error": "No audio found in the file"}
    if channels == "mono" and samples.shape[1] > 1:
        samples = samples.mean(axis=1, keepdims=True)
    elif channels == "stereo" and samples.shape[1] == 1:
        samples = np.repeat(samples, 2, axis=1)
    speed = max(25, min(speed_percent, 400)) / 100
    if speed != 1:
        idx = np.arange(0, len(samples), speed)
        samples = np.stack(
            [np.interp(idx, np.arange(len(samples)), samples[:, c]) for c in range(samples.shape[1])], axis=1
        )
    samples = samples * (max(0, min(volume_percent, 1000)) / 100)
    if normalize == "yes":
        peak = np.abs(samples).max()
        if peak > 0:
            samples = samples / peak * 0.98
    n = len(samples)
    fade_in = min(int(max(0.0, fade_in_seconds) * rate), n)
    fade_out = min(int(max(0.0, fade_out_seconds) * rate), n)
    if fade_in:
        samples[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    if fade_out:
        samples[n - fade_out :] *= np.linspace(1, 0, fade_out)[:, None]
    samples = np.clip(samples, -1, 1)
    out = audio.with_name(f"{audio.stem}_adjusted.{output}")
    _encode(out, samples, rate, output)
    return {
        "file": out,
        "duration_seconds": round(n / rate, 2),
        "channels": samples.shape[1],
        "sample_rate": rate,
        "peak": round(float(np.abs(samples).max()), 3),
    }


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
    codec = {"mp3": "mp3", "wav": "pcm_s16le", "flac": "flac", "ogg": "libopus"}[fmt]
    out_rate = 48000 if codec == "libopus" else rate
    if out_rate != rate:
        idx = np.arange(0, len(samples), rate / out_rate)
        samples = np.stack(
            [np.interp(idx, np.arange(len(samples)), samples[:, c]) for c in range(samples.shape[1])], axis=1
        )
    layout = "mono" if samples.shape[1] == 1 else "stereo"
    with closing(av.open(str(path), mode="w")) as container:
        stream = container.add_stream(codec, rate=out_rate, layout=layout)
        step = 4096
        for start in range(0, len(samples), step):
            block = np.ascontiguousarray(samples[start : start + step].T.astype(np.float32))
            frame = av.AudioFrame.from_ndarray(block, format="fltp", layout=layout)
            frame.sample_rate = out_rate
            frame.pts = None
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
