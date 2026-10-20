# time, epoch, unix, timestamp, date, converter

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import re


def epoch_converter(input: str = "now", timezone_name: str = "UTC") -> dict:
    """Convert a Unix timestamp (seconds, milliseconds, microseconds or nanoseconds are auto-detected) to human dates, or a date like 2026-10-19 14:30 to a timestamp. 'now' gives the current time."""
    try:
        tz = ZoneInfo(timezone_name.strip() or "UTC")
    except Exception:  # noqa: BLE001
        return {"error": f"Unknown time zone '{timezone_name}'. Use IANA names such as UTC, Europe/London, America/New_York."}

    text = input.strip()
    unit = "seconds"
    if text.lower() in ("", "now"):
        when = datetime.now(timezone.utc)
    elif re.fullmatch(r"-?\d+(\.\d+)?", text):
        number = float(text)
        magnitude = abs(number)
        if magnitude >= 1e17:
            unit, number = "nanoseconds", number / 1e9
        elif magnitude >= 1e14:
            unit, number = "microseconds", number / 1e6
        elif magnitude >= 1e11:
            unit, number = "milliseconds", number / 1e3
        when = datetime.fromtimestamp(number, timezone.utc)
    else:
        candidate = text.replace("T", " ").replace("Z", "+00:00")
        formats = ["%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M%z",
                   "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                   "%d/%m/%Y %H:%M", "%d/%m/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"]
        when = None
        for fmt in formats:
            try:
                when = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue
        if when is None:
            return {"error": f"Could not understand '{input}'. Try 1700000000, 2026-10-19 14:30, or 19/10/2026."}
        if when.tzinfo is None:
            when = when.replace(tzinfo=tz)

    utc = when.astimezone(timezone.utc)
    local = when.astimezone(tz)
    epoch = utc.timestamp()
    delta = datetime.now(timezone.utc) - utc
    seconds = abs(delta.total_seconds())
    if seconds < 60:
        rel = f"{int(seconds)} seconds"
    elif seconds < 3600:
        rel = f"{int(seconds // 60)} minutes"
    elif seconds < 86400:
        rel = f"{seconds / 3600:.1f} hours"
    else:
        rel = f"{seconds / 86400:.1f} days"
    relative = f"{rel} ago" if delta > timedelta(0) else f"in {rel}"

    return {
        "input_interpreted_as": unit if re.fullmatch(r"-?\d+(\.\d+)?", text) else "date",
        "epoch_seconds": int(epoch),
        "epoch_milliseconds": int(epoch * 1000),
        "iso_8601_utc": utc.isoformat().replace("+00:00", "Z"),
        f"local_{tz.key}": local.strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)"),
        "rfc_2822": utc.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "weekday": utc.strftime("%A"),
        "day_of_year": utc.timetuple().tm_yday,
        "iso_week": f"{utc.isocalendar()[0]}-W{utc.isocalendar()[1]:02d}",
        "relative": relative,
    }
