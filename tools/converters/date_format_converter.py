# date, format, reformat, csv, text, converter

from pathlib import Path
from typing import Literal
from datetime import datetime
import re

INPUT_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%Y%m%d",
]
OUTPUT_FORMATS = {
    "iso_2026_10_20": "%Y-%m-%d",
    "us_10_20_2026": "%m/%d/%Y",
    "uk_20_10_2026": "%d/%m/%Y",
    "european_20_10_2026": "%d.%m.%Y",
    "long_October_20_2026": "%B %d, %Y",
    "long_20_October_2026": "%d %B %Y",
    "compact_20261020": "%Y%m%d",
    "weekday_long": "%A, %d %B %Y",
}


def date_format_converter(
    text_file: Path,
    output_format: Literal[
        "iso_2026_10_20",
        "us_10_20_2026",
        "uk_20_10_2026",
        "european_20_10_2026",
        "long_October_20_2026",
        "long_20_October_2026",
        "compact_20261020",
        "weekday_long",
    ] = "iso_2026_10_20",
    day_first: Literal["no", "yes"] = "no",
) -> dict:
    """Find every date in a text or CSV file (ISO, US, UK, European, long and compact
    forms) and rewrite it in one chosen format. Ambiguous 03/04/2026 is read
    month-first unless day_first.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    formats = INPUT_FORMATS[:]
    if day_first == "yes":
        formats.remove("%d/%m/%Y")
        formats.insert(0, "%d/%m/%Y")
    pattern = (
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
        r"|[A-Z][a-z]+ \d{1,2}, \d{4}|\d{1,2} [A-Z][a-z]+ \d{4}|\d{8})\b"
    )
    count = 0

    def swap(m):
        nonlocal count
        s = m.group(0)
        for fmt in formats:
            try:
                parsed = datetime.strptime(s, fmt)
            except ValueError:
                continue
            count += 1
            return parsed.strftime(OUTPUT_FORMATS[output_format])
        return s

    result = re.sub(pattern, swap, text)
    out = text_file.with_name(f"{text_file.stem}_dates{text_file.suffix or '.txt'}")
    out.write_text(result, encoding="utf-8")
    return {"file": out, "dates_converted": count}
