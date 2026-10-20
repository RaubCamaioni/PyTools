# timestamp, epoch, ldap, snowflake, objectid, julian, ticks, converter

from datetime import datetime, timedelta, timezone
from typing import Literal

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def timestamp_decoder(
    value: str = "1700000000",
    format: Literal[
        "auto",
        "unix_seconds",
        "unix_milliseconds",
        "ldap_windows_filetime",
        "dotnet_ticks",
        "twitter_discord_snowflake",
        "mongodb_objectid",
        "julian_day",
        "excel_serial",
        "gps_seconds",
        "iso_date",
    ] = "auto",
) -> dict:
    """Decode the timestamp formats programmers meet: Unix seconds/milliseconds, Windows
    FILETIME / LDAP, .NET ticks, Twitter and Discord snowflakes, MongoDB ObjectIds,
    Julian days, Excel serial dates and GPS seconds, into one UTC date, plus that
    date in every other format.
    """
    text = value.strip()
    fmt = format
    if fmt == "auto":
        if len(text) == 24 and all(c in "0123456789abcdefABCDEF" for c in text):
            fmt = "mongodb_objectid"
        elif text.isdigit():
            n = int(text)
            fmt = (
                "excel_serial"
                if n < 100_000
                else (
                    "unix_seconds"
                    if n < 10**11
                    else (
                        "unix_milliseconds"
                        if n < 10**14
                        else (
                            "twitter_discord_snowflake"
                            if n < 10**19 and len(text) <= 19 and n > 10**16
                            else "ldap_windows_filetime"
                        )
                    )
                )
            )
        elif "." in text and text.replace(".", "").isdigit():
            fmt = "julian_day" if float(text) > 1_000_000 else "excel_serial"
        else:
            fmt = "iso_date"
    try:
        when = _decode(text, fmt)
    except (ValueError, OverflowError) as e:
        return {"error": f"Could not read '{value}' as {fmt}: {e}"}

    seconds = (when - EPOCH).total_seconds()
    return {
        "interpreted_as": fmt,
        "utc": when.isoformat(),
        "unix_seconds": int(seconds),
        "unix_milliseconds": int(seconds * 1000),
        "ldap_windows_filetime": int((seconds + 11644473600) * 10**7),
        "dotnet_ticks": int((seconds + 62135596800) * 10**7),
        "julian_day": round(seconds / 86400 + 2440587.5, 6),
        "excel_serial": round(seconds / 86400 + 25569, 6),
        "gps_seconds": int(seconds - 315964800),
        "twitter_snowflake_min": (
            int((seconds * 1000 - 1288834974657) * 2**22) if seconds * 1000 > 1288834974657 else None
        ),
        "discord_snowflake_min": (
            int((seconds * 1000 - 1420070400000) * 2**22) if seconds * 1000 > 1420070400000 else None
        ),
        "mongodb_objectid_prefix": f"{int(seconds):08x}" + "0" * 16,
    }


def _decode(text: str, fmt: str) -> datetime:
    if fmt == "unix_seconds":
        return EPOCH + timedelta(seconds=float(text))
    if fmt == "unix_milliseconds":
        return EPOCH + timedelta(milliseconds=float(text))
    if fmt == "ldap_windows_filetime":
        return EPOCH + timedelta(microseconds=int(text) / 10) - timedelta(seconds=11644473600)
    if fmt == "dotnet_ticks":
        return datetime(1, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=int(text) / 10)
    if fmt == "twitter_discord_snowflake":
        ms = int(text) >> 22
        epoch_ms = 1420070400000 if ms + 1420070400000 < 4102444800000 and int(text) >= 2**50 else 1288834974657
        return EPOCH + timedelta(milliseconds=ms + epoch_ms)
    if fmt == "mongodb_objectid":
        return EPOCH + timedelta(seconds=int(text[:8], 16))
    if fmt == "julian_day":
        return EPOCH + timedelta(days=float(text) - 2440587.5)
    if fmt == "excel_serial":
        return EPOCH + timedelta(days=float(text) - 25569)
    if fmt == "gps_seconds":
        return EPOCH + timedelta(seconds=float(text) + 315964800)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
