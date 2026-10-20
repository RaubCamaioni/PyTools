# audio, silence, trim, split, channels, stereo

from pathlib import Path
from typing import Literal
from contextlib import closing
import wave
import numpy as np
import av


def audio_silence_trim(
    audio: Path,
    action: Literal["trim_silence_at_ends", "remove_all_silence", "split_stereo_to_two_mono"] = "trim_silence_at_ends",
    threshold_db: float = -40,
) -> dict:
    """Cut the silence from the start and end of a recording, remove every silent gap
    longer than half a second, or split a stereo file into separate left and right
    WAV files.
    """
    samples, rate = _decode(audio)
    if samples.size == 0:
        return {"error": "No audio found"}
    if action == "split_stereo_to_two_mono":
        if samples.shape[1] < 2:
            return {"error": "The file is mono; nothing to split"}
        left, right = audio.with_name(f"{audio.stem}_left.wav"), audio.with_name(f"{audio.stem}_right.wav")
        _write_wav(left, samples[:, :1], rate)
        _write_wav(right, samples[:, 1:2], rate)
        return {"left": left, "right": right, "duration_seconds": round(len(samples) / rate, 2)}
    level = 10 ** (threshold_db / 20)
    window = max(1, rate // 50)
    loud = np.abs(samples).max(axis=1)
    blocks = np.array([loud[i : i + window].max() for i in range(0, len(loud), window)]) > level
    if not blocks.any():
        return {"error": "The whole file is below the silence threshold"}
    if action == "trim_silence_at_ends":
        first, last = np.argmax(blocks), len(blocks) - np.argmax(blocks[::-1])
        kept = samples[first * window : last * window]
    else:
        keep = blocks.copy()
        run = 0
        for i, b in enumerate(blocks):
            run = 0 if b else run + 1
            if run <= 25:
                keep[i] = True
        kept = np.concatenate([samples[i * window : (i + 1) * window] for i, k in enumerate(keep) if k])
    out = audio.with_name(f"{audio.stem}_{action}.wav")
    _write_wav(out, kept, rate)
    return {"file": out, "before_seconds": round(len(samples) / rate, 2), "after_seconds": round(len(kept) / rate, 2)}


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


def _write_wav(path: Path, samples: np.ndarray, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(samples.shape[1])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
