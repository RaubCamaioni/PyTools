# markdown, html, document, converter

from pathlib import Path
from typing import Literal
import html
import markdown

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{
  max-width: 46rem; margin: 2rem auto; padding: 0 1rem;
  font-family: system-ui, sans-serif; line-height: 1.6; color: #222;
}}
pre {{ background: #f4f4f4; padding: .75rem; overflow-x: auto; }}
code {{ background: #f4f4f4; padding: .1rem .3rem; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #ccc; padding: .3rem .6rem; }}
blockquote {{ border-left: 4px solid #ccc; margin-left: 0; padding-left: 1rem; color: #555; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def markdown_to_html(markdown_file: Path, output: Literal["full_page", "fragment"] = "full_page") -> Path:
    """Render a Markdown file to HTML (tables, fenced code, footnotes and task lists supported)."""
    text = markdown_file.read_text(encoding="utf-8-sig", errors="replace")
    body = markdown.markdown(text, extensions=["extra", "sane_lists", "toc", "nl2br"])
    out = markdown_file.with_suffix(".html")
    if output == "fragment":
        out.write_text(body + "\n", encoding="utf-8")
    else:
        out.write_text(PAGE.format(title=html.escape(markdown_file.stem), body=body), encoding="utf-8")
    return out
