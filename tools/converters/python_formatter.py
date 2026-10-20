# python, black, format, lint

from pathlib import Path
import black


def python_formatter(python_file: Path, line_length: int = 120) -> dict:
    """Format a Python file with black (the style used by this site's tools) and report
    whether anything changed. A syntax error is reported with its line instead of a
    formatted file.
    """
    text = python_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        result = black.format_str(text, mode=black.Mode(line_length=max(40, min(line_length, 200))))
    except black.InvalidInput as e:
        return {"error": f"Cannot parse: {e}"}
    out = python_file.with_name(f"{python_file.stem}_formatted.py")
    out.write_text(result, encoding="utf-8")
    return {"file": out, "changed": result != text, "lines": result.count("\n")}
