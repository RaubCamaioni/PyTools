# unit, weight, mass, kilogram, pound, converter

from typing import Literal

# kilograms per unit
UNITS = {
    "milligram": 1e-6,
    "gram": 0.001,
    "kilogram": 1.0,
    "metric_ton": 1000.0,
    "ounce": 0.028349523125,
    "pound": 0.45359237,
    "stone": 6.35029318,
    "us_ton": 907.18474,
    "imperial_ton": 1016.0469088,
    "carat": 0.0002,
    "grain": 0.00006479891,
}


def weight_converter(
    value: float = 1,
    unit: Literal[
        "kilogram",
        "gram",
        "milligram",
        "metric_ton",
        "pound",
        "ounce",
        "stone",
        "us_ton",
        "imperial_ton",
        "carat",
        "grain",
    ] = "kilogram",
) -> dict:
    """Convert a weight/mass between kg, g, mg, tonnes, pounds, ounces, stone and more."""
    kg = value * UNITS[unit]
    result = {name: float(f"{kg / factor:.6g}") for name, factor in UNITS.items()}
    total_ounces = kg / UNITS["ounce"]
    pounds, ounces = divmod(total_ounces, 16)
    result["pounds_and_ounces"] = f"{int(pounds)} lb {ounces:.2f} oz"
    stones, rem = divmod(kg / UNITS["pound"], 14)
    result["stone_and_pounds"] = f"{int(stones)} st {rem:.2f} lb"
    return result
