# unit, volume, liter, gallon, cup, cooking, converter

from typing import Literal

# litres per unit
UNITS = {
    "milliliter": 0.001,
    "liter": 1.0,
    "cubic_meter": 1000.0,
    "cubic_centimeter": 0.001,
    "cubic_inch": 0.016387064,
    "cubic_foot": 28.316846592,
    "us_teaspoon": 0.00492892159375,
    "us_tablespoon": 0.01478676478125,
    "us_fluid_ounce": 0.0295735295625,
    "us_cup": 0.2365882365,
    "us_pint": 0.473176473,
    "us_quart": 0.946352946,
    "us_gallon": 3.785411784,
    "imperial_fluid_ounce": 0.0284130625,
    "imperial_pint": 0.56826125,
    "imperial_quart": 1.1365225,
    "imperial_gallon": 4.54609,
    "metric_cup": 0.25,
}


def volume_converter(
    value: float = 1,
    unit: Literal[
        "liter", "milliliter", "cubic_meter", "cubic_centimeter", "cubic_inch", "cubic_foot",
        "us_teaspoon", "us_tablespoon", "us_fluid_ounce", "us_cup", "us_pint", "us_quart", "us_gallon",
        "imperial_fluid_ounce", "imperial_pint", "imperial_quart", "imperial_gallon", "metric_cup",
    ] = "liter",
) -> dict:
    """Convert a volume between litres, millilitres, cubic metres, US and imperial gallons, pints, cups, tablespoons and teaspoons."""
    litres = value * UNITS[unit]
    return {name: float(f"{litres / factor:.6g}") for name, factor in UNITS.items()}
