# audio, waveform, spectrogram, image, visualize

from pathlib import Path
from typing import Literal
from contextlib import closing
import numpy as np
import av
from PIL import Image, ImageDraw


def audio_visualizer(
    audio: Path,
    style: Literal["waveform", "spectrogram"] = "waveform",
    width: int = 1200,
    height: int = 300,
) -> dict:
    """Draw an audio file as a waveform or a spectrogram PNG (time left to right; the
    spectrogram shows frequency bottom to top on a log scale).
    """
    width, height = max(200, min(width, 4000)), max(100, min(height, 2000))
    chunks, rate = [], 44100
    with closing(av.open(str(audio))) as container:
        stream = container.streams.audio[0]
        rate = stream.rate
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=rate)
        for frame in container.decode(stream):
            for f in resampler.resample(frame):
                chunks.append(f.to_ndarray()[0])
    if not chunks:
        return {"error": "No audio found"}
    samples = np.concatenate(chunks)
    duration = len(samples) / rate

    if style == "waveform":
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        mid = height / 2
        per_column = max(1, len(samples) // width)
        for x in range(width):
            block = samples[x * per_column : (x + 1) * per_column]
            if block.size:
                lo, hi = block.min(), block.max()
                draw.line((x, mid - hi * mid * 0.95, x, mid - lo * mid * 0.95), fill=(30, 100, 200))
        draw.line((0, mid, width, mid), fill=(180, 180, 180))
    else:
        window = 1024
        hop = max(1, len(samples) // width)
        columns = []
        hann = np.hanning(window)
        for x in range(width):
            start = x * hop
            block = samples[start : start + window]
            if len(block) < window:
                block = np.pad(block, (0, window - len(block)))
            spectrum = np.abs(np.fft.rfft(block * hann))
            columns.append(spectrum)
        spec = np.array(columns).T
        spec = 20 * np.log10(spec + 1e-6)
        spec = np.clip((spec - spec.max() + 80) / 80, 0, 1)
        freqs = np.arange(spec.shape[0]) * rate / window
        log_rows = np.geomspace(max(20, freqs[1]), rate / 2, height)
        rows = np.searchsorted(freqs, log_rows)
        rows = np.clip(rows, 0, spec.shape[0] - 1)
        picture = spec[rows][::-1]
        rgb = np.stack([picture**0.5 * 255, picture**2 * 255, np.sqrt(picture) * 120 + picture * 135], axis=-1)
        img = Image.fromarray(rgb.astype(np.uint8), "RGB").resize((width, height))
    out = audio.with_name(f"{audio.stem}_{style}.png")
    img.save(out)
    return {"file": out, "duration_seconds": round(duration, 2), "sample_rate": rate}
