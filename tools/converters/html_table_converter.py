# html, table, csv, converter, scrape

from pathlib import Path
from typing import Literal
from html.parser import HTMLParser
import csv
import html


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def html_table_converter(
    file: Path, direction: Literal["html_to_csv", "csv_to_html"] = "html_to_csv", table_number: int = 1
) -> dict:
    """Pull a table out of an HTML page into CSV (choose which table by number), or turn
    a CSV into a clean HTML table snippet with a header row.
    """
    text = file.read_text(encoding="utf-8-sig", errors="replace")
    if direction == "csv_to_html":
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = [r for r in csv.reader(text.splitlines(), dialect=dialect) if r]
        if not rows:
            return {"error": "The CSV is empty"}
        parts = [
            "<table>",
            "  <thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in rows[0]) + "</tr></thead>",
            "  <tbody>",
        ]
        parts += ["    <tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:]]
        parts += ["  </tbody>", "</table>"]
        out = file.with_suffix(".html")
        out.write_text("\n".join(parts) + "\n", encoding="utf-8")
        return {"file": out, "rows": len(rows) - 1, "columns": len(rows[0])}
    reader = TableReader()
    reader.feed(text)
    if not reader.tables:
        return {"error": "No <table> found in the HTML"}
    index = max(1, min(table_number, len(reader.tables))) - 1
    rows = reader.tables[index]
    out = file.with_name(f"{file.stem}_table{index + 1}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return {"file": out, "tables_found": len(reader.tables), "rows": len(rows), "columns": max(len(r) for r in rows)}
