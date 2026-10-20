# unit, time, duration, seconds, hours, days, converter

from typing import Literal

# seconds per unit
UNITS = {
    "millisecond": 0.001,
    "second": 1.0,
    "minute": 60.0,
    "hour": 3600.0,
    "day": 86400.0,
    "week": 604800.0,
    "month_30d": 2592000.0,
    "year_365d": 31536000.0,
}


def time_duration_converter(
    value: float = 90,
    unit: Literal["minute", "second", "millisecond", "hour", "day", "week", "month_30d", "year_365d"] = "minute",
) -> dict:
    """Convert a duration between milliseconds, seconds, minutes, hours, days, weeks, months and years, with an hh:mm:ss breakdown."""
    seconds = value * UNITS[unit]
    result = {name: float(f"{seconds / factor:.6g}") for name, factor in UNITS.items()}
    total = int(round(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    result["hh_mm_ss"] = f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}" if days else f"{hours:02d}:{minutes:02d}:{secs:02d}"
    parts = []
    for label, amount in (("day", days), ("hour", hours), ("minute", minutes), ("second", secs)):
        if amount:
            parts.append(f"{amount} {label}{'s' if amount != 1 else ''}")
    result["human_readable"] = ", ".join(parts) or "0 seconds"
    return result
