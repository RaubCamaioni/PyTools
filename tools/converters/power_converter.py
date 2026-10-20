# unit, power, watt, horsepower, kilowatt, converter

from typing import Literal
import math

# watts per unit
UNITS = {
    "watt": 1.0,
    "milliwatt": 0.001,
    "kilowatt": 1000.0,
    "megawatt": 1e6,
    "gigawatt": 1e9,
    "mechanical_horsepower": 745.69987158227022,
    "metric_horsepower_PS": 735.49875,
    "btu_per_hour": 0.29307107,
    "ton_of_refrigeration": 3516.8528420667,
    "foot_pound_per_second": 1.3558179483314004,
}


def power_converter(
    value: float = 1,
    unit: Literal[
        "kilowatt",
        "watt",
        "milliwatt",
        "megawatt",
        "gigawatt",
        "mechanical_horsepower",
        "metric_horsepower_PS",
        "btu_per_hour",
        "ton_of_refrigeration",
        "foot_pound_per_second",
        "dBm",
    ] = "kilowatt",
) -> dict:
    """Convert power between watts, kW, MW, horsepower (mechanical and metric PS),
    BTU/h, tons of refrigeration and dBm.
    """
    watts = 10 ** ((value - 30) / 10) if unit == "dBm" else value * UNITS[unit]
    result = {name: float(f"{watts / factor:.6g}") for name, factor in UNITS.items()}
    result["dBm"] = float(f"{10 * math.log10(watts * 1000):.6g}") if watts > 0 else "undefined"
    result["dBW"] = float(f"{10 * math.log10(watts):.6g}") if watts > 0 else "undefined"
    return result
