# unit, pressure, pascal, bar, psi, atmosphere, converter

from typing import Literal

# pascals per unit
UNITS = {
    "pascal": 1.0,
    "kilopascal": 1000.0,
    "megapascal": 1e6,
    "bar": 100000.0,
    "millibar_hPa": 100.0,
    "atmosphere": 101325.0,
    "psi": 6894.757293168,
    "torr_mmHg": 133.32236842105263,
    "inHg": 3386.388640341,
    "kgf_per_cm2": 98066.5,
}


def pressure_converter(
    value: float = 1,
    unit: Literal[
        "bar",
        "psi",
        "pascal",
        "kilopascal",
        "megapascal",
        "millibar_hPa",
        "atmosphere",
        "torr_mmHg",
        "inHg",
        "kgf_per_cm2",
    ] = "bar",
) -> dict:
    """Convert pressure between pascals, kPa, bar, millibar/hPa, atmospheres, psi, torr/mmHg, inHg and kgf/cm2 (tyres,
    weather, diving).
    """
    pa = value * UNITS[unit]
    return {name: float(f"{pa / factor:.6g}") for name, factor in UNITS.items()}
