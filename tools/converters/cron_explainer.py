# cron, schedule, crontab, explain, time

from datetime import datetime, timezone
from cron_descriptor import get_description
from croniter import croniter


def cron_explainer(expression: str = "*/15 9-17 * * 1-5", upcoming: int = 5) -> dict:
    """Explain a cron expression in plain English and list its next run times (UTC).
    Accepts the five-field crontab form and @daily / @hourly style shortcuts.
    """
    text = expression.strip()
    shortcuts = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly": "0 * * * *",
    }
    text = shortcuts.get(text.lower(), text)
    if not croniter.is_valid(text):
        return {"error": f"'{expression}' is not a valid cron expression (minute hour day month weekday)"}
    now = datetime.now(timezone.utc)
    it = croniter(text, now)
    runs = [it.get_next(datetime).strftime("%Y-%m-%d %H:%M UTC (%a)") for _ in range(max(1, min(upcoming, 20)))]
    try:
        description = get_description(text)
    except Exception as e:  # noqa: BLE001 - the description is best effort
        description = f"(no description: {e})"
    fields = dict(zip(["minute", "hour", "day_of_month", "month", "day_of_week"], text.split()))
    return {"expression": text, "meaning": description, "fields": fields, "next_runs": runs}
