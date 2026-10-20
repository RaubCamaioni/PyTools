# unit, speed, velocity, mph, kmh, knots, converter

from typing import Literal

# metres per second per unit
UNITS = {
    "meters_per_second": 1.0,
    "kilometers_per_hour": 1000 / 3600,
    "miles_per_hour": 1609.344 / 3600,
    "feet_per_second": 0.3048,
    "knots": 1852 / 3600,
    "mach_sea_level": 340.29,
    "speed_of_light": 299792458.0,
}


def speed_converter(
    value: float = 100,
    unit: Literal[
        "kilometers_per_hour",
        "miles_per_hour",
        "meters_per_second",
        "feet_per_second",
        "knots",
        "mach_sea_level",
        "speed_of_light",
    ] = "kilometers_per_hour",
) -> dict:
    """Convert a speed between km/h, mph, m/s, ft/s, knots and Mach, plus the
    minutes-per-km and minutes-per-mile pace.
    """
    mps = value * UNITS[unit]
    result = {name: float(f"{mps / factor:.6g}") for name, factor in UNITS.items()}
    if mps > 0:
        for label, metres in (("pace_min_per_km", 1000), ("pace_min_per_mile", 1609.344)):
            seconds = metres / mps
            result[label] = f"{int(seconds // 60)}:{int(seconds % 60):02d}"
    return result
