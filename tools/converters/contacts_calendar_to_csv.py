# vcf, ics, contacts, calendar, csv, converter

from pathlib import Path
import csv
import re


def contacts_calendar_to_csv(file: Path) -> dict:
    """Convert a vCard contacts file (.vcf) or an iCalendar file (.ics) into a CSV
    spreadsheet: one row per contact or event with name, email, phone, dates,
    location and so on.
    """
    text = file.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    text = re.sub(r"\n[ \t]", "", text)  # unfold continuation lines
    kind = "contacts" if "BEGIN:VCARD" in text.upper() else "events" if "BEGIN:VEVENT" in text.upper() else None
    if kind is None:
        return {"error": "Expected a .vcf (BEGIN:VCARD) or .ics (BEGIN:VEVENT) file"}
    tag = "VCARD" if kind == "contacts" else "VEVENT"
    blocks = re.findall(rf"BEGIN:{tag}(.*?)END:{tag}", text, re.S | re.I)
    wanted = (
        ["FN", "N", "EMAIL", "TEL", "ORG", "TITLE", "ADR", "BDAY", "URL", "NOTE"]
        if kind == "contacts"
        else ["SUMMARY", "DTSTART", "DTEND", "LOCATION", "DESCRIPTION", "ORGANIZER", "STATUS", "RRULE", "UID"]
    )
    rows = []
    for block in blocks:
        row = {k: [] for k in wanted}
        for line in block.strip().split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            name = key.split(";")[0].upper()
            if name in row:
                row[name].append(value.replace("\\,", ",").replace("\\n", " ").replace(";", " ").strip())
        rows.append({k: " | ".join(v) for k, v in row.items()})
    out = file.with_suffix(".csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=wanted)
        writer.writeheader()
        writer.writerows(rows)
    return {"file": out, kind: len(rows)}
