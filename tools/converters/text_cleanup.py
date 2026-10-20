# text, clean, whitespace, accents, punctuation

from pathlib import Path
from typing import Literal
import re
import unicodedata


def text_cleanup(
    text_file: Path,
    operation: Literal[
        "collapse_whitespace",
        "remove_all_whitespace",
        "remove_accents",
        "remove_punctuation",
        "remove_numbers",
        "remove_html_tags",
        "remove_empty_lines",
        "tabs_to_spaces",
        "spaces_to_tabs",
        "add_thousands_separators",
        "smart_quotes_to_plain",
    ],
) -> Path:
    """Clean up a text file: collapse or strip whitespace, drop accents, punctuation,
    numbers or HTML tags, swap tabs and spaces, add thousands separators to numbers,
    or straighten curly quotes.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")

    if operation == "collapse_whitespace":
        text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    elif operation == "remove_all_whitespace":
        text = re.sub(r"\s+", "", text)
    elif operation == "remove_accents":
        text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    elif operation == "remove_punctuation":
        text = "".join(c for c in text if not unicodedata.category(c).startswith("P"))
    elif operation == "remove_numbers":
        text = re.sub(r"\d+", "", text)
    elif operation == "remove_html_tags":
        text = re.sub(r"<[^>]+>", "", text)
    elif operation == "remove_empty_lines":
        text = "\n".join(line for line in text.splitlines() if line.strip())
    elif operation == "tabs_to_spaces":
        text = text.expandtabs(4)
    elif operation == "spaces_to_tabs":
        text = re.sub(r"^((?:    )+)", lambda m: "\t" * (len(m.group(1)) // 4), text, flags=re.M)
    elif operation == "add_thousands_separators":
        text = re.sub(r"(?<![\d.])\d{4,}(?![\d.])", lambda m: f"{int(m.group(0)):,}", text)
    else:
        text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "--"}))

    out = text_file.with_name(f"{text_file.stem}_{operation}{text_file.suffix or '.txt'}")
    out.write_text(text, encoding="utf-8")
    return out
