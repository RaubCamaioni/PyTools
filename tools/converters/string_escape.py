# text, escape, json, shell, csv, sql, converter

from typing import Literal
import html
import json
import shlex


def string_escape(
    input: str,
    language: Literal["json", "python", "shell", "csv", "sql", "html_attribute", "regex", "xml"],
    mode: Literal["escape", "unescape"],
) -> str:
    """Escape a string for use inside JSON, Python, a shell command, a CSV cell, a SQL
    literal, an HTML attribute, a regular expression or XML, or unescape it back.
    """
    if mode == "escape":
        if language == "json":
            return json.dumps(input)
        if language == "python":
            return repr(input)
        if language == "shell":
            return shlex.quote(input)
        if language == "csv":
            return '"' + input.replace('"', '""') + '"' if any(c in input for c in ',"\n') else input
        if language == "sql":
            return "'" + input.replace("'", "''") + "'"
        if language == "html_attribute":
            return html.escape(input, quote=True)
        if language == "regex":
            import re

            return re.escape(input)
        return input.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = input.strip()
    try:
        if language == "json":
            return json.loads(text if text.startswith('"') else json.dumps(text))
        if language == "python":
            import ast

            return ast.literal_eval(text) if text[:1] in "'\"" else text
        if language == "shell":
            return " ".join(shlex.split(text))
        if language == "csv":
            return text[1:-1].replace('""', '"') if text.startswith('"') and text.endswith('"') else text
        if language == "sql":
            return text[1:-1].replace("''", "'") if text.startswith("'") and text.endswith("'") else text
        if language in ("html_attribute", "xml"):
            return html.unescape(text)
        return text.replace("\\", "")
    except (ValueError, SyntaxError) as e:
        return f"Could not unescape as {language}: {e}"
