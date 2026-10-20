# svg, optimize, minify, clean, vector

from pathlib import Path
from scour import scour


def svg_optimizer(svg: Path, precision: int = 3) -> dict:
    """Shrink an SVG file without changing how it looks: strip editor metadata, comments
    and unused definitions, shorten ids and round coordinates to the given number of
    digits.
    """
    text = svg.read_text(encoding="utf-8-sig", errors="replace")
    before = len(text.encode("utf-8"))
    options = scour.sanitizeOptions()
    options.remove_metadata = True
    options.strip_comments = True
    options.strip_ids = True
    options.shorten_ids = True
    options.digits = max(1, min(precision, 10))
    options.indent_type = "none"
    options.newlines = False
    try:
        result = scour.scourString(text, options)
    except Exception as e:  # noqa: BLE001 - scour raises bare exceptions on malformed XML
        return {"error": f"Not a valid SVG: {e}"}
    out = svg.with_name(f"{svg.stem}.min.svg")
    out.write_text(result, encoding="utf-8")
    after = out.stat().st_size
    return {
        "file": out,
        "before_bytes": before,
        "after_bytes": after,
        "saved": f"{(1 - after / before) * 100:.1f}%" if before else "n/a",
    }
