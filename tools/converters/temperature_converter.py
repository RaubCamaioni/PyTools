# unit, temperature, celsius, fahrenheit, kelvin, converter

from typing import Literal


def temperature_converter(
    value: float = 20,
    unit: Literal["celsius", "fahrenheit", "kelvin", "rankine"] = "celsius",
) -> dict:
    """Convert a temperature between Celsius, Fahrenheit, Kelvin and Rankine."""
    if unit == "celsius":
        c = value
    elif unit == "fahrenheit":
        c = (value - 32) * 5 / 9
    elif unit == "kelvin":
        c = value - 273.15
    else:
        c = (value - 491.67) * 5 / 9

    return {
        "celsius": round(c, 4),
        "fahrenheit": round(c * 9 / 5 + 32, 4),
        "kelvin": round(c + 273.15, 4),
        "rankine": round((c + 273.15) * 9 / 5, 4),
        "note": "water freezes at 0 °C / 32 °F / 273.15 K and boils at 100 °C / 212 °F / 373.15 K",
    }
