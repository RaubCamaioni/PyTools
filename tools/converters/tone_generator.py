# audio, tone, sine, noise, test, generator

from pathlib import Path
from typing import Literal
import wave
import numpy as np


def tone_generator(
    frequency_hz: float = 440,
    seconds: float = 3,
    waveform: Literal[
        "sine", "square", "triangle", "sawtooth", "white_noise", "pink_noise", "sweep_20_to_20k"
    ] = "sine",
    volume_percent: int = 50,
) -> Path:
    """Generate a test tone or noise as a WAV file: sine, square, triangle, sawtooth,
    white or pink noise, or a 20 Hz to 20 kHz sweep. Handy for speaker tests, tuning
    and hearing checks.
    """
    rate = 44100
    seconds = max(0.1, min(seconds, 120))
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    f = max(1.0, min(frequency_hz, 20000))
    if waveform == "sine":
        signal = np.sin(2 * np.pi * f * t)
    elif waveform == "square":
        signal = np.sign(np.sin(2 * np.pi * f * t))
    elif waveform == "triangle":
        signal = 2 * np.abs(2 * ((t * f) % 1) - 1) - 1
    elif waveform == "sawtooth":
        signal = 2 * ((t * f) % 1) - 1
    elif waveform == "white_noise":
        signal = np.random.uniform(-1, 1, len(t))
    elif waveform == "pink_noise":
        white = np.random.normal(0, 1, len(t))
        spectrum = np.fft.rfft(white)
        spectrum /= np.sqrt(np.arange(1, len(spectrum) + 1))
        signal = np.fft.irfft(spectrum, n=len(t))
        signal /= np.abs(signal).max()
    else:
        phase = 2 * np.pi * 20 * seconds / np.log(1000) * (np.exp(t / seconds * np.log(1000)) - 1)
        signal = np.sin(phase)
    fade = min(int(rate * 0.01), len(t) // 2)
    signal[:fade] *= np.linspace(0, 1, fade)
    signal[-fade:] *= np.linspace(1, 0, fade)
    signal *= max(0, min(volume_percent, 100)) / 100
    out = Path(f"{waveform}_{int(f)}hz_{seconds:g}s.wav")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((signal * 32767).astype(np.int16).tobytes())
    return out
