# csv, markdown, table, converter

from pathlib import Path
from typing import Literal
import csv
import re


def csv_to_markdown_table(
    data_file: Path,
    direction: Literal["csv_to_markdown", "markdown_to_csv"],
    align_numbers_right: Literal["yes", "no"] = "yes",
) -> Path:
    """Turn a CSV file into a Markdown table (padded columns), or a Markdown table back
    into CSV.
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")

    if direction == "markdown_to_csv":
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        out = data_file.with_suffix(".csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        return out

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [row for row in csv.reader(text.splitlines(), dialect=dialect) if row]
    if not rows:
        raise ValueError("CSV file is empty")
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    widths = [max(len(r[i]) for r in rows) for i in range(width)]
    widths = [max(w, 3) for w in widths]

    def numeric(col: int) -> bool:
        body = [r[col] for r in rows[1:] if r[col].strip()]
        return bool(body) and all(re.fullmatch(r"[-+]?[\d,]*\.?\d+%?", v.strip()) for v in body)

    right = [align_numbers_right == "yes" and numeric(i) for i in range(width)]

    def fmt(row: list[str]) -> str:
        cells = [(c.rjust(widths[i]) if right[i] else c.ljust(widths[i])) for i, c in enumerate(row)]
        return "| " + " | ".join(cells) + " |"

    sep = "| " + " | ".join(("-" * (widths[i] - 1) + ":") if right[i] else "-" * widths[i] for i in range(width)) + " |"
    lines = [fmt(rows[0]), sep] + [fmt(r) for r in rows[1:]]
    out = data_file.with_suffix(".md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
