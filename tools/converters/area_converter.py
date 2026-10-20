# unit, area, acre, hectare, square, converter

from typing import Literal

# square metres per unit
UNITS = {
    "square_millimeter": 1e-6,
    "square_centimeter": 1e-4,
    "square_meter": 1.0,
    "hectare": 10000.0,
    "square_kilometer": 1e6,
    "square_inch": 0.00064516,
    "square_foot": 0.09290304,
    "square_yard": 0.83612736,
    "acre": 4046.8564224,
    "square_mile": 2589988.110336,
}


def area_converter(
    value: float = 1,
    unit: Literal[
        "square_meter",
        "square_centimeter",
        "square_millimeter",
        "hectare",
        "square_kilometer",
        "square_inch",
        "square_foot",
        "square_yard",
        "acre",
        "square_mile",
    ] = "square_meter",
) -> dict:
    """Convert an area between square metres, hectares, square kilometres, square feet,
    square yards, acres and square miles.
    """
    m2 = value * UNITS[unit]
    return {name: float(f"{m2 / factor:.6g}") for name, factor in UNITS.items()}
