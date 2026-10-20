# time, timezone, date, converter

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

COMMON = [
    "UTC", "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York", "America/Sao_Paulo",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow", "Africa/Johannesburg", "Asia/Dubai",
    "Asia/Kolkata", "Asia/Shanghai", "Asia/Tokyo", "Australia/Sydney", "Pacific/Auckland",
]


def find_zone(name: str) -> ZoneInfo:
    name = name.strip()
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001
        pass
    lowered = name.lower().replace(" ", "_")
    aliases = {"est": "America/New_York", "edt": "America/New_York", "cst": "America/Chicago", "cdt": "America/Chicago",
               "mst": "America/Denver", "mdt": "America/Denver", "pst": "America/Los_Angeles", "pdt": "America/Los_Angeles",
               "gmt": "Europe/London", "bst": "Europe/London", "cet": "Europe/Paris", "cest": "Europe/Paris",
               "ist": "Asia/Kolkata", "jst": "Asia/Tokyo", "aest": "Australia/Sydney", "aedt": "Australia/Sydney"}
    if lowered in aliases:
        return ZoneInfo(aliases[lowered])
    for zone in available_timezones():
        if zone.lower().endswith("/" + lowered) or zone.lower() == lowered:
            return ZoneInfo(zone)
    raise ValueError(f"Unknown time zone '{name}'. Use IANA names like Europe/London or America/New_York.")


def timezone_converter(
    time: str = "now",
    from_zone: str = "UTC",
    to_zone: str = "America/New_York",
) -> dict:
    """Convert a date/time from one time zone to another and show it in the world's major cities. Accepts IANA names (Europe/Paris), city names (Tokyo) or abbreviations (PST, CET)."""
    src = find_zone(from_zone)
    dst = find_zone(to_zone)
    text = time.strip()
    if text.lower() in ("", "now"):
        when = datetime.now(src)
    else:
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%H:%M", "%I:%M %p", "%I %p"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return {"error": f"Could not understand '{time}'. Try 2026-10-19 14:30, 14:30 or 2:30 PM."}
        if parsed.year == 1900:  # time-only formats: use today's date
            today = datetime.now(src)
            parsed = parsed.replace(year=today.year, month=today.month, day=today.day)
        when = parsed.replace(tzinfo=src)

    target = when.astimezone(dst)
    fmt = "%Y-%m-%d %H:%M %Z (UTC%z)"
    offset_hours = (target.utcoffset() - when.utcoffset()).total_seconds() / 3600
    world = {zone: when.astimezone(ZoneInfo(zone)).strftime("%a %H:%M %Z") for zone in COMMON}
    return {
        "from": f"{when.strftime(fmt)} [{src.key}]",
        "to": f"{target.strftime(fmt)} [{dst.key}]",
        "difference_hours": offset_hours,
        "world_clock": world,
    }
