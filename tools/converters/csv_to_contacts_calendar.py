# csv, vcf, ics, contacts, calendar, converter

from pathlib import Path
from typing import Literal
import csv
import re
from datetime import datetime


def csv_to_contacts_calendar(data_file: Path, output: Literal["vcf_contacts", "ics_calendar"] = "vcf_contacts") -> dict:
    """Turn a CSV into a vCard contacts file (columns like name, email, phone,
    organisation) or an iCalendar file (columns like summary, start, end, location,
    description) that phones, Outlook and Google import directly. Column names are
    matched loosely.
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    if not rows:
        return {"error": "The CSV has no rows"}

    def pick(row: dict, *keys: str) -> str:
        for k in row:
            if any(key in k.lower().replace(" ", "_") for key in keys):
                if row[k]:
                    return str(row[k]).strip()
        return ""

    if output == "vcf_contacts":
        cards = []
        for r in rows:
            name = pick(r, "full_name", "name") or (pick(r, "first") + " " + pick(r, "last")).strip()
            if not name:
                continue
            lines = [
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"FN:{name}",
                f"N:{pick(r, 'last') or name.split()[-1]};{pick(r, 'first') or ' '.join(name.split()[:-1])};;;",
            ]
            for value, prop in (
                (pick(r, "email", "mail"), "EMAIL"),
                (pick(r, "phone", "tel", "mobile"), "TEL;TYPE=CELL"),
                (pick(r, "org", "company"), "ORG"),
                (pick(r, "title", "job"), "TITLE"),
                (pick(r, "url", "website"), "URL"),
                (pick(r, "note"), "NOTE"),
            ):
                if value:
                    lines.append(f"{prop}:{value}")
            lines.append("END:VCARD")
            cards.append("\r\n".join(lines))
        out = data_file.with_suffix(".vcf")
        out.write_text("\r\n".join(cards) + "\r\n", encoding="utf-8")
        return {"file": out, "contacts": len(cards)}

    def stamp(value: str) -> str:
        for fmt in (
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ):
            try:
                d = datetime.strptime(value.strip(), fmt)
                return d.strftime("%Y%m%d") if fmt.endswith("%Y") or fmt == "%Y-%m-%d" else d.strftime("%Y%m%dT%H%M%S")
            except ValueError:
                continue
        return ""

    events = []
    for i, r in enumerate(rows, 1):
        summary = pick(r, "summary", "title", "event", "name")
        start = stamp(pick(r, "start", "date", "begin"))
        if not summary or not start:
            continue
        end = stamp(pick(r, "end", "finish")) or start
        kind = ";VALUE=DATE" if len(start) == 8 else ""
        lines = [
            "BEGIN:VEVENT",
            f"UID:pytools-{i}-{re.sub(r'[^a-z0-9]', '', summary.lower())[:20]}",
            f"DTSTART{kind}:{start}",
            f"DTEND{kind}:{end}",
            f"SUMMARY:{summary}",
        ]
        for value, prop in (
            (pick(r, "location", "place"), "LOCATION"),
            (pick(r, "description", "notes", "details"), "DESCRIPTION"),
        ):
            if value:
                lines.append(f"{prop}:{value.replace(chr(10), ' ')}")
        lines.append("END:VEVENT")
        events.append("\r\n".join(lines))
    out = data_file.with_suffix(".ics")
    out.write_text(
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//PyTools//EN\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR\r\n",
        encoding="utf-8",
    )
    return {"file": out, "events": len(events)}
