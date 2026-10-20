# sql, format, beautify, minify

from pathlib import Path
from typing import Literal
import sqlparse


def sql_formatter(
    sql_file: Path,
    action: Literal["beautify", "minify"] = "beautify",
    keywords: Literal["upper", "lower", "keep"] = "upper",
) -> Path:
    """Beautify SQL (one clause per line, indented, keywords upper- or lower-cased) or
    squeeze it onto one line.
    """
    text = sql_file.read_text(encoding="utf-8-sig", errors="replace")
    case = None if keywords == "keep" else keywords
    if action == "minify":
        result = sqlparse.format(text, strip_comments=True, keyword_case=case, reindent=False, strip_whitespace=True)
        result = " ".join(result.split())
    else:
        result = sqlparse.format(text, reindent=True, keyword_case=case, indent_width=4, wrap_after=100)
    out = sql_file.with_name(f"{sql_file.stem}_{action}.sql")
    out.write_text(result.strip() + "\n", encoding="utf-8")
    return out
