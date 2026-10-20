# unit, data, bytes, storage, bandwidth, converter

from typing import Literal

# bytes per unit
UNITS = {
    "bit": 1 / 8,
    "byte": 1,
    "kilobyte_KB": 1000,
    "megabyte_MB": 1000**2,
    "gigabyte_GB": 1000**3,
    "terabyte_TB": 1000**4,
    "petabyte_PB": 1000**5,
    "kibibyte_KiB": 1024,
    "mebibyte_MiB": 1024**2,
    "gibibyte_GiB": 1024**3,
    "tebibyte_TiB": 1024**4,
    "pebibyte_PiB": 1024**5,
    "kilobit_kb": 125,
    "megabit_Mb": 125_000,
    "gigabit_Gb": 125_000_000,
}


def data_size_converter(
    value: float = 1,
    unit: Literal[
        "gigabyte_GB", "megabyte_MB", "kilobyte_KB", "terabyte_TB", "petabyte_PB", "byte", "bit",
        "gibibyte_GiB", "mebibyte_MiB", "kibibyte_KiB", "tebibyte_TiB", "pebibyte_PiB",
        "kilobit_kb", "megabit_Mb", "gigabit_Gb",
    ] = "gigabyte_GB",
) -> dict:
    """Convert data sizes between bits, bytes, decimal units (KB, MB, GB, TB) and binary units (KiB, MiB, GiB, TiB), plus transfer time at common speeds."""
    total_bytes = value * UNITS[unit]
    result = {name: float(f"{total_bytes / factor:.6g}") for name, factor in UNITS.items()}
    bits = total_bytes * 8
    times = {}
    for label, mbps in (("10_Mbps", 10), ("100_Mbps", 100), ("1_Gbps", 1000)):
        seconds = bits / (mbps * 1e6)
        if seconds < 60:
            times[label] = f"{seconds:.2f} s"
        elif seconds < 3600:
            times[label] = f"{seconds / 60:.2f} min"
        else:
            times[label] = f"{seconds / 3600:.2f} h"
    result["transfer_time_at"] = times
    return result
