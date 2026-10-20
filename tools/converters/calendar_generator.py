# calendar, month, year, print, generator

from pathlib import Path
from typing import Literal
import calendar
import datetime


def calendar_generator(
    year: int = 2026,
    month: int = 0,
    first_weekday: Literal["monday", "sunday"] = "monday",
    output: Literal["text", "html", "csv_dates"] = "text",
) -> Path:
    """Print a month (or the whole year when month is 0) as a text calendar, an HTML
    table, or a CSV of every date with its weekday, ISO week and day of year.
    """
    calendar.setfirstweekday(calendar.MONDAY if first_weekday == "monday" else calendar.SUNDAY)
    year = max(1, min(year, 9999))
    label = f"{year}" if month == 0 else f"{year}-{month:02d}"
    if output == "csv_dates":
        months = range(1, 13) if month == 0 else [month]
        lines = ["date,weekday,iso_week,day_of_year"]
        for m in months:
            for d in range(1, calendar.monthrange(year, m)[1] + 1):
                day = datetime.date(year, m, d)
                lines.append(f"{day.isoformat()},{day.strftime('%A')},{day.isocalendar()[1]},{day.timetuple().tm_yday}")
        out = Path(f"calendar_{label}.csv")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out
    if output == "html":
        html_cal = calendar.HTMLCalendar(calendar.firstweekday())
        body = html_cal.formatyear(year, width=3) if month == 0 else html_cal.formatmonth(year, month)
        style = (
            "<style>table{border-collapse:collapse;font-family:sans-serif}"
            "td,th{border:1px solid #ccc;padding:4px 8px;text-align:center}th{background:#eee}</style>"
        )
        out = Path(f"calendar_{label}.html")
        out.write_text(
            f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body>{body}</body></html>\n",
            encoding="utf-8",
        )
        return out
    text_cal = calendar.TextCalendar(calendar.firstweekday())
    text = text_cal.formatyear(year, 2, 1, 6, 3) if month == 0 else text_cal.formatmonth(year, month)
    out = Path(f"calendar_{label}.txt")
    out.write_text(text, encoding="utf-8")
    return out
