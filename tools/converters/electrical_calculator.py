# electrical, ohm, watts, amps, volts, calculator

from typing import Literal


def electrical_calculator(
    known_1: Literal["volts", "amps", "ohms", "watts"] = "volts",
    value_1: float = 230,
    known_2: Literal["volts", "amps", "ohms", "watts"] = "watts",
    value_2: float = 2000,
    hours_per_day: float = 1,
    price_per_kwh: float = 0.30,
) -> dict:
    """Ohm's law and power: give any two of volts, amps, ohms and watts and get the
    other two, plus the energy used per day/month/year and what it costs at your
    electricity price.
    """
    if known_1 == known_2:
        return {"error": "Choose two different quantities"}
    k = {known_1: value_1, known_2: value_2}
    v, i, r, p = k.get("volts"), k.get("amps"), k.get("ohms"), k.get("watts")
    try:
        if v is not None and i is not None:
            r, p = v / i, v * i
        elif v is not None and r is not None:
            i, p = v / r, v * v / r
        elif v is not None and p is not None:
            i, r = p / v, v * v / p
        elif i is not None and r is not None:
            v, p = i * r, i * i * r
        elif i is not None and p is not None:
            v, r = p / i, p / (i * i)
        else:
            v, i = (p * r) ** 0.5, (p / r) ** 0.5
    except ZeroDivisionError:
        return {"error": "Division by zero; check the values"}
    kwh_day = p / 1000 * max(0.0, hours_per_day)
    return {
        "volts": round(v, 4),
        "amps": round(i, 4),
        "ohms": round(r, 4),
        "watts": round(p, 4),
        "kilowatts": round(p / 1000, 4),
        "horsepower": round(p / 745.7, 4),
        "energy_kwh_per_day": round(kwh_day, 3),
        "energy_kwh_per_month": round(kwh_day * 30, 2),
        "energy_kwh_per_year": round(kwh_day * 365, 1),
        "cost_per_year": round(kwh_day * 365 * price_per_kwh, 2),
        "fuse_suggestion_amps": next(
            (f for f in (1, 2, 3, 5, 6, 10, 13, 16, 20, 25, 32, 40, 63) if f >= i * 1.25), "over 63"
        ),
    }
