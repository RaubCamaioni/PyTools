# text, extract, emails, urls, numbers, phone, regex

from pathlib import Path
from typing import Literal
import re

PATTERNS = {
    "emails": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "urls": r"https?://[^\s<>\"')\]]+",
    "numbers": r"[-+]?\d[\d,]*\.?\d*",
    "phone_numbers": r"\+?\d[\d\s().-]{7,}\d",
    "hashtags": r"#\w+",
    "mentions": r"@\w+",
    "ip_addresses": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "dates": r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    "capitalised_words": r"\b[A-Z][a-z]+\b",
}


def text_extractor(
    text_file: Path,
    extract: Literal[
        "emails",
        "urls",
        "numbers",
        "phone_numbers",
        "hashtags",
        "mentions",
        "ip_addresses",
        "dates",
        "capitalised_words",
    ],
    unique: Literal["yes", "no"] = "yes",
) -> Path:
    """Pull every email address, URL, number, phone number, hashtag, mention, IP, date
    or capitalised word out of a text file into a list, one per line.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    found = [m.group(0).strip() for m in re.finditer(PATTERNS[extract], text)]
    if unique == "yes":
        found = list(dict.fromkeys(found))
    out = text_file.with_name(f"{text_file.stem}_{extract}.txt")
    out.write_text(("\n".join(found) + "\n") if found else f"no {extract.replace('_', ' ')} found\n", encoding="utf-8")
    return out
