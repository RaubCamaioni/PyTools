# text, find, replace, regex, bulk

from pathlib import Path
from typing import Literal
import re


def find_replace(
    text_file: Path,
    find: str,
    replace: str = "",
    mode: Literal["plain_text", "regex", "whole_word"] = "plain_text",
    case_sensitive: Literal["yes", "no"] = "yes",
) -> dict:
    """Find and replace throughout a text file: plain text, whole words only, or a
    regular expression (use \\1 for groups in the replacement). Reports how many
    matches were replaced.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    flags = 0 if case_sensitive == "yes" else re.IGNORECASE
    if mode == "plain_text":
        pattern = re.escape(find)
    elif mode == "whole_word":
        pattern = r"\b" + re.escape(find) + r"\b"
    else:
        pattern = find
    try:
        regex = re.compile(pattern, flags)
        new_text, count = regex.subn(replace if mode == "regex" else replace.replace("\\", "\\\\"), text)
    except re.error as e:
        return {"error": f"Invalid pattern: {e}"}
    out = text_file.with_name(f"{text_file.stem}_replaced{text_file.suffix or '.txt'}")
    out.write_text(new_text, encoding="utf-8")
    return {"file": out, "replacements": count}
