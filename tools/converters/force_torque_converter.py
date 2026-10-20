# unit, force, torque, newton, pound, converter

from typing import Literal

FORCE = {
    "newton": 1.0,
    "kilonewton": 1000.0,
    "pound_force": 4.4482216152605,
    "kilogram_force": 9.80665,
    "dyne": 1e-5,
    "ounce_force": 0.27801385,
}
TORQUE = {
    "newton_meter": 1.0,
    "newton_centimeter": 0.01,
    "foot_pound": 1.3558179483314004,
    "inch_pound": 0.1129848290276167,
    "kilogram_force_meter": 9.80665,
    "inch_ounce": 0.00706155,
}


def force_torque_converter(
    value: float = 10,
    unit: Literal[
        "newton",
        "kilonewton",
        "pound_force",
        "kilogram_force",
        "dyne",
        "ounce_force",
        "newton_meter",
        "newton_centimeter",
        "foot_pound",
        "inch_pound",
        "kilogram_force_meter",
        "inch_ounce",
    ] = "newton_meter",
) -> dict:
    """Convert force (N, kN, lbf, kgf, dyne) or torque (N·m, ft·lb, in·lb, kgf·m)
    between units; the family is chosen by the unit you enter.
    """
    table = FORCE if unit in FORCE else TORQUE
    base = value * table[unit]
    return {name: float(f"{base / factor:.6g}") for name, factor in table.items()}
