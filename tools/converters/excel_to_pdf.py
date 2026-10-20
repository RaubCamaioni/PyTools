# excel, xlsx, csv, pdf, table, converter

from pathlib import Path
from typing import Literal
import csv
import html
import pymupdf

STYLE = """
body { font-family: sans-serif; font-size: %dpt; }
h2 { font-size: 1.3em; margin: 0 0 6pt 0; }
table { border-collapse: collapse; width: 100%%; }
td, th { border: 0.5pt solid #999; padding: 2pt 4pt; vertical-align: top; }
th { background: #eee; font-weight: bold; }
"""


def excel_to_pdf(
    spreadsheet: Path,
    orientation: Literal["landscape", "portrait"] = "landscape",
    font_size: int = 9,
    header_row: Literal["yes", "no"] = "yes",
) -> Path:
    """Print an Excel workbook (every sheet) or a CSV file to a PDF table. Cell values and number formats are kept;
    charts, merged-cell layouts and colours are not.
    """
    sheets: list[tuple[str, list[list[str]]]] = []
    if spreadsheet.suffix.lower() in (".csv", ".tsv", ".txt"):
        text = spreadsheet.read_text(encoding="utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        sheets.append((spreadsheet.stem, [list(r) for r in csv.reader(text.splitlines(), dialect=dialect)]))
    else:
        from openpyxl import load_workbook

        wb = load_workbook(str(spreadsheet), read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                if row is None or all(v is None for v in row):
                    continue
                rows.append(["" if v is None else (f"{v:g}" if isinstance(v, float) else str(v)) for v in row])
            if rows:
                sheets.append((ws.title, rows))
    if not sheets:
        raise ValueError("No data found in the spreadsheet")

    parts = []
    for title, rows in sheets:
        width = max(len(r) for r in rows)
        body = []
        for i, row in enumerate(rows[:5000]):
            cells = row + [""] * (width - len(row))
            tag = "th" if (i == 0 and header_row == "yes") else "td"
            body.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>")
        parts.append(f"<h2>{html.escape(title)}</h2><table>{''.join(body)}</table>")

    width, height = (842, 595) if orientation == "landscape" else (595, 842)
    story = pymupdf.Story(
        html="<body>" + "<p></p>".join(parts) + "</body>", user_css=STYLE % max(5, min(font_size, 20))
    )
    out = spreadsheet.with_suffix(".pdf")
    writer = pymupdf.DocumentWriter(str(out))
    margin = 36
    box = pymupdf.Rect(margin, margin, width - margin, height - margin)
    more, pages = True, 0
    while more and pages < 2000:
        device = writer.begin_page(pymupdf.Rect(0, 0, width, height))
        more, _ = story.place(box)
        story.draw(device)
        writer.end_page()
        pages += 1
    writer.close()
    return out
