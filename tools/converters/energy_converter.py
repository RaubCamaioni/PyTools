# unit, energy, joule, calorie, kwh, btu, converter

from typing import Literal

# joules per unit
UNITS = {
    "joule": 1.0,
    "kilojoule": 1000.0,
    "megajoule": 1e6,
    "calorie": 4.184,
    "kilocalorie_food_Calorie": 4184.0,
    "watt_hour": 3600.0,
    "kilowatt_hour": 3.6e6,
    "btu": 1055.05585262,
    "therm": 105505585.262,
    "electronvolt": 1.602176634e-19,
    "foot_pound": 1.3558179483314004,
    "erg": 1e-7,
}


def energy_converter(
    value: float = 1,
    unit: Literal[
        "kilowatt_hour",
        "joule",
        "kilojoule",
        "megajoule",
        "calorie",
        "kilocalorie_food_Calorie",
        "watt_hour",
        "btu",
        "therm",
        "electronvolt",
        "foot_pound",
        "erg",
    ] = "kilowatt_hour",
) -> dict:
    """Convert energy between joules, calories, kilocalories (food Calories),
    watt-hours, kWh, BTU, therms, electronvolts and foot-pounds.
    """
    joules = value * UNITS[unit]
    return {name: float(f"{joules / factor:.6g}") for name, factor in UNITS.items()}
