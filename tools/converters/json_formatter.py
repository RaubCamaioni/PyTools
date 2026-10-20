# json, format, minify, validate, converter

from pathlib import Path
from typing import Literal
import json


def json_formatter(
    json_file: Path,
    action: Literal["pretty_print", "minify", "sort_keys", "validate"],
    indent: int = 2,
) -> Path:
    """Pretty-print, minify, sort the keys of, or validate a JSON file. Reports the line
    and column of any syntax error.
    """
    text = json_file.read_text(encoding="utf-8-sig", errors="replace")
    output = json_file.with_name(f"{json_file.stem}_{action}.json")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        report = json_file.with_name(f"{json_file.stem}_error.txt")
        report.write_text(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}\n")
        return report

    if action == "validate":
        report = json_file.with_name(f"{json_file.stem}_valid.txt")
        kind = type(data).__name__
        size = len(data) if isinstance(data, (list, dict)) else 1
        report.write_text(f"Valid JSON. Top level: {kind} with {size} item(s).\n")
        return report

    if action == "minify":
        output.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    elif action == "sort_keys":
        output.write_text(
            json.dumps(data, indent=max(0, indent), sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    else:
        output.write_text(json.dumps(data, indent=max(0, indent), ensure_ascii=False) + "\n", encoding="utf-8")
    return output
