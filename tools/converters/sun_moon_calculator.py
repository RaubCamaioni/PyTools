# sunrise, sunset, moon, phase, daylight, astronomy

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
from astral import LocationInfo, moon
from astral.sun import sun


def sun_moon_calculator(
    latitude: float = 51.5,
    longitude: float = -0.12,
    day: str = "today",
    timezone_name: str = "UTC",
) -> dict:
    """Sunrise, sunset, dawn, dusk, solar noon and day length for a place and date, plus
    the moon phase. Coordinates in decimal degrees (north and east positive).
    """
    try:
        tz = ZoneInfo(timezone_name.strip() or "UTC")
    except Exception:  # noqa: BLE001
        return {"error": f"Unknown time zone '{timezone_name}'"}
    when = date.today() if day.strip().lower() in ("", "today") else date.fromisoformat(day.strip())
    place = LocationInfo("here", "", tz.key, latitude, longitude)
    try:
        s = sun(place.observer, date=when, tzinfo=tz)
    except ValueError as e:
        return {"error": f"The sun does not rise or set there on that date: {e}"}
    fmt = lambda t: t.strftime("%H:%M")  # noqa: E731
    length = s["sunset"] - s["sunrise"]
    phase = moon.phase(when)
    names = [
        "new moon",
        "waxing crescent",
        "first quarter",
        "waxing gibbous",
        "full moon",
        "waning gibbous",
        "last quarter",
        "waning crescent",
    ]
    illumination = round((1 - math.cos(phase / 29.53 * 2 * math.pi)) / 2 * 100)
    return {
        "date": when.isoformat(),
        "time_zone": tz.key,
        "dawn": fmt(s["dawn"]),
        "sunrise": fmt(s["sunrise"]),
        "solar_noon": fmt(s["noon"]),
        "sunset": fmt(s["sunset"]),
        "dusk": fmt(s["dusk"]),
        "day_length": f"{int(length.total_seconds() // 3600)}h {int(length.total_seconds() % 3600 // 60)}m",
        "moon_phase": names[int(phase / 29.53 * 8 + 0.5) % 8],
        "moon_age_days": round(phase, 1),
        "moon_illumination_percent": illumination,
        "next_full_moon_approx": (when + timedelta(days=(14.77 - phase) % 29.53)).isoformat(),
    }
