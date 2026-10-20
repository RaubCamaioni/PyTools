# docx, word, text, markdown, document, converter

from pathlib import Path
from typing import Literal
from docx import Document


def docx_to_text(docx_file: Path, output: Literal["plain_text", "markdown"] = "plain_text") -> Path:
    """Extract the text of a Word .docx file (paragraphs and tables) as plain text or
    Markdown with headings, lists and tables.
    """
    doc = Document(str(docx_file))
    lines: list[str] = []
    md = output == "markdown"

    def run_text(paragraph) -> str:
        if not md:
            return paragraph.text
        parts = []
        for run in paragraph.runs:
            t = run.text
            if not t.strip():
                parts.append(t)
                continue
            if run.bold:
                t = f"**{t}**"
            if run.italic:
                t = f"*{t}*"
            parts.append(t)
        return "".join(parts)

    for block in doc.element.body.iterchildren():
        tag = block.tag.split("}")[-1]
        if tag == "p":
            from docx.text.paragraph import Paragraph

            p = Paragraph(block, doc)
            style = (p.style.name or "").lower() if p.style is not None else ""
            text = run_text(p).strip()
            if not text:
                lines.append("")
                continue
            if md and style.startswith("heading"):
                level = "".join(ch for ch in style if ch.isdigit()) or "1"
                lines.extend(["", "#" * min(int(level), 6) + " " + text, ""])
            elif md and "list" in style:
                lines.append("- " + text)
            elif md:
                lines.extend([text, ""])
            else:
                lines.append(text)
        elif tag == "tbl":
            from docx.table import Table

            table = Table(block, doc)
            rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells] for row in table.rows]
            if not rows:
                continue
            if md:
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "---|" * len(rows[0]))
                for r in rows[1:]:
                    lines.append("| " + " | ".join(r) + " |")
            else:
                for r in rows:
                    lines.append("\t".join(r))
            lines.append("")

    out = docx_file.with_suffix(".md" if md else ".txt")
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return out
