# javascript, css, json, beautify, minify, format

from pathlib import Path
from typing import Literal
import cssbeautifier
import jsbeautifier
import rcssmin
import rjsmin


def web_code_formatter(
    code_file: Path,
    language: Literal["javascript", "css"] = "javascript",
    action: Literal["beautify", "minify"] = "beautify",
    indent: int = 2,
) -> dict:
    """Beautify (indent, one statement per line) or minify JavaScript and CSS files.
    Reports the size before and after.
    """
    text = code_file.read_text(encoding="utf-8-sig", errors="replace")
    before = len(text.encode("utf-8"))
    ext = "js" if language == "javascript" else "css"
    if action == "minify":
        result = rjsmin.jsmin(text) if language == "javascript" else rcssmin.cssmin(text)
        out = code_file.with_name(f"{code_file.stem}.min.{ext}")
    else:
        options = jsbeautifier.default_options()
        options.indent_size = max(1, min(indent, 8))
        result = (
            jsbeautifier.beautify(text, options) if language == "javascript" else cssbeautifier.beautify(text, options)
        )
        out = code_file.with_name(f"{code_file.stem}_pretty.{ext}")
    out.write_text(result.strip() + "\n", encoding="utf-8")
    after = out.stat().st_size
    return {
        "file": out,
        "before_bytes": before,
        "after_bytes": after,
        "change": f"{(after / before - 1) * 100:+.1f}%" if before else "n/a",
    }
