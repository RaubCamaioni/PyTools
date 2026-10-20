# unit, length, distance, metric, imperial, converter

from typing import Literal

# metres per unit
UNITS = {
    "millimeter": 0.001,
    "centimeter": 0.01,
    "meter": 1.0,
    "kilometer": 1000.0,
    "inch": 0.0254,
    "foot": 0.3048,
    "yard": 0.9144,
    "mile": 1609.344,
    "nautical_mile": 1852.0,
    "micrometer": 1e-6,
    "nanometer": 1e-9,
    "light_year": 9.4607304725808e15,
    "astronomical_unit": 149597870700.0,
}


def length_converter(
    value: float = 1,
    unit: Literal[
        "meter",
        "centimeter",
        "millimeter",
        "kilometer",
        "inch",
        "foot",
        "yard",
        "mile",
        "nautical_mile",
        "micrometer",
        "nanometer",
        "astronomical_unit",
        "light_year",
    ] = "meter",
) -> dict:
    """Convert a length or distance between metric and imperial units (mm, cm, m, km,
    in, ft, yd, mi and more).
    """
    metres = value * UNITS[unit]
    result = {name: float(f"{metres / factor:.6g}") for name, factor in UNITS.items()}
    total_inches = metres / 0.0254
    feet, inches = divmod(total_inches, 12)
    result["feet_and_inches"] = f"{int(feet)} ft {inches:.2f} in"
    return result
