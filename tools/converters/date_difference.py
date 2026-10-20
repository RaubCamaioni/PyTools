# date, time, duration, calculator

from datetime import datetime, timedelta
import calendar


def parse(text: str) -> datetime:
    text = text.strip()
    if text.lower() in ("", "now", "today"):
        return datetime.now()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not understand date '{text}'. Use YYYY-MM-DD (optionally with HH:MM).")


def date_difference(start_date: str = "2000-01-01", end_date: str = "today") -> dict:
    """Days, weeks, months, years and business days between two dates (age calculator,
    countdown, date diff).
    """
    start = parse(start_date)
    end = parse(end_date)
    if end < start:
        start, end = end, start
    delta = end - start

    def add_months(when: datetime, count: int) -> datetime:
        month_index = when.month - 1 + count
        year = when.year + month_index // 12
        month = month_index % 12 + 1
        day = min(when.day, calendar.monthrange(year, month)[1])
        return when.replace(year=year, month=month, day=day)

    total_months = (end.year - start.year) * 12 + (end.month - start.month)
    while total_months > 0 and add_months(start, total_months) > end:
        total_months -= 1
    years, months = divmod(total_months, 12)
    days = (end - add_months(start, total_months)).days

    business = 0
    cursor = start.date()
    while cursor < end.date():
        if cursor.weekday() < 5:
            business += 1
        cursor += timedelta(days=1)

    return {
        "from": start.strftime("%A %Y-%m-%d %H:%M"),
        "to": end.strftime("%A %Y-%m-%d %H:%M"),
        "years_months_days": f"{years} years, {months} months, {days} days",
        "total_days": delta.days,
        "total_weeks": round(delta.days / 7, 2),
        "total_months_approx": round(delta.days / 30.436875, 2),
        "total_years_approx": round(delta.days / 365.2425, 3),
        "total_hours": round(delta.total_seconds() / 3600, 1),
        "total_minutes": int(delta.total_seconds() // 60),
        "business_days": business,
        "weekend_days": delta.days - business,
    }
