# unit, bandwidth, data rate, mbps, download time, converter

from typing import Literal

UNITS = {
    "bits_per_second": 1,
    "kilobits_per_second": 1e3,
    "megabits_per_second": 1e6,
    "gigabits_per_second": 1e9,
    "bytes_per_second": 8,
    "kilobytes_per_second": 8e3,
    "megabytes_per_second": 8e6,
    "gigabytes_per_second": 8e9,
}


def data_rate_converter(
    value: float = 100,
    unit: Literal[
        "megabits_per_second",
        "kilobits_per_second",
        "gigabits_per_second",
        "bits_per_second",
        "bytes_per_second",
        "kilobytes_per_second",
        "megabytes_per_second",
        "gigabytes_per_second",
    ] = "megabits_per_second",
    file_size_gb: float = 4.7,
) -> dict:
    """Convert connection speeds between bits and bytes per second (the Mbps vs MB/s
    confusion), and work out how long a file of a given size takes at that speed.
    """
    bps = value * UNITS[unit]
    result = {name: float(f"{bps / factor:.6g}") for name, factor in UNITS.items()}
    if bps > 0:
        seconds = file_size_gb * 8e9 / bps
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        result[f"time_for_{file_size_gb:g}_GB"] = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"
        result["gigabytes_per_hour"] = float(f"{bps * 3600 / 8e9:.4g}")
        result["monthly_cap_usage_at_full_speed_tb"] = float(f"{bps * 3600 * 24 * 30 / 8e12:.4g}")
    return result
