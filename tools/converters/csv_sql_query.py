# csv, sql, query, data, sqlite

from pathlib import Path
from typing import Literal
import csv
import json
import sqlite3


def csv_sql_query(
    data_file: Path,
    sql: str = "SELECT * FROM data LIMIT 20",
    output: Literal["csv", "json", "markdown"] = "csv",
) -> dict:
    """Run a SQL query against a CSV file: the file is loaded into a SQLite table called
    `data` with its header row as column names, so GROUP BY, ORDER BY, WHERE and
    aggregates all work.
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect=dialect))
    if len(rows) < 1:
        return {"error": "The CSV is empty"}
    header = [h.strip() or f"column{i + 1}" for i, h in enumerate(rows[0])]
    width = len(header)

    def typed(value: str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    db = sqlite3.connect(":memory:")
    quoted = ", ".join(f'"{h}"' for h in header)
    db.execute(f"CREATE TABLE data ({quoted})")
    db.executemany(
        f"INSERT INTO data VALUES ({', '.join('?' * width)})",
        [[typed(v) for v in (r + [""] * width)[:width]] for r in rows[1:]],
    )
    try:
        cursor = db.execute(sql)
        result = cursor.fetchmany(10_000)
        columns = [d[0] for d in cursor.description] if cursor.description else []
    except sqlite3.Error as e:
        return {"error": f"SQL error: {e}", "columns_available": header}

    out = data_file.with_name(f"{data_file.stem}_query.{ 'md' if output == 'markdown' else output}")
    if output == "json":
        out.write_text(json.dumps([dict(zip(columns, r)) for r in result], indent=2, default=str), encoding="utf-8")
    elif output == "markdown":
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        lines += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in result]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(result)
    return {"file": out, "rows": len(result), "columns": columns}
