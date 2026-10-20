# markdown, toc, table of contents, headings, document

from pathlib import Path
from typing import Literal
import re


def markdown_toc(
    markdown_file: Path,
    max_level: int = 3,
    action: Literal["toc_only", "insert_into_document"] = "toc_only",
) -> Path:
    """Build a table of contents (GitHub-style anchor links) from the headings of a
    Markdown file, either on its own or inserted at the top of the document.
    """
    text = markdown_file.read_text(encoding="utf-8-sig", errors="replace")
    lines, in_code, entries, seen = [], False, [], {}
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not m or len(m.group(1)) > max(1, min(max_level, 6)):
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        slug = re.sub(r"[^\w\- ]", "", title.lower()).strip().replace(" ", "-")
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0
        entries.append("  " * (level - 1) + f"- [{title}](#{slug})")
    toc = "\n".join(entries) + "\n" if entries else "(no headings found)\n"
    if action == "toc_only":
        out = markdown_file.with_name(f"{markdown_file.stem}_toc.md")
        out.write_text(toc, encoding="utf-8")
        return out
    out = markdown_file.with_name(f"{markdown_file.stem}_with_toc.md")
    out.write_text("## Table of contents\n\n" + toc + "\n" + text, encoding="utf-8")
    return out
