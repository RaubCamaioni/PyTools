# unit, fuel, mpg, economy, car, converter

from typing import Literal


def fuel_economy_converter(
    value: float = 30,
    unit: Literal["mpg_us", "mpg_imperial", "liters_per_100km", "km_per_liter"] = "mpg_us",
) -> dict:
    """Convert fuel economy between US mpg, imperial mpg, L/100 km and km/L."""
    if value <= 0:
        return {"error": "Enter a value greater than zero."}
    if unit == "mpg_us":
        l_per_100 = 235.214583 / value
    elif unit == "mpg_imperial":
        l_per_100 = 282.480936 / value
    elif unit == "km_per_liter":
        l_per_100 = 100 / value
    else:
        l_per_100 = value
    return {
        "liters_per_100km": round(l_per_100, 3),
        "km_per_liter": round(100 / l_per_100, 3),
        "mpg_us": round(235.214583 / l_per_100, 3),
        "mpg_imperial": round(282.480936 / l_per_100, 3),
        "miles_per_liter": round(235.214583 / l_per_100 / 3.785411784, 3),
    }
