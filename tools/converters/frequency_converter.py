# unit, frequency, hertz, rpm, bpm, period, wavelength, converter

from typing import Literal

UNITS = {
    "hertz": 1.0,
    "kilohertz": 1e3,
    "megahertz": 1e6,
    "gigahertz": 1e9,
    "rpm": 1 / 60,
    "bpm": 1 / 60,
    "radians_per_second": 1 / (2 * 3.141592653589793),
}


def frequency_converter(
    value: float = 440,
    unit: Literal["hertz", "kilohertz", "megahertz", "gigahertz", "rpm", "bpm", "radians_per_second"] = "hertz",
) -> dict:
    """Convert frequency between Hz, kHz, MHz, GHz, RPM, BPM and rad/s, with the period,
    the wavelength in air and in vacuum, and the nearest musical note.
    """
    hz = value * UNITS[unit]
    result = {name: float(f"{hz / factor:.6g}") for name, factor in UNITS.items()}
    if hz > 0:
        result["period_seconds"] = float(f"{1 / hz:.6g}")
        result["wavelength_sound_in_air_m"] = float(f"{343 / hz:.6g}")
        result["wavelength_radio_in_vacuum_m"] = float(f"{299792458 / hz:.6g}")
        import math

        n = round(12 * math.log2(hz / 440))
        names = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
        octave = 4 + (n + 9) // 12
        cents = round(1200 * math.log2(hz / (440 * 2 ** (n / 12))))
        result["nearest_note"] = f"{names[n % 12]}{octave} ({cents:+d} cents)"
    return result
