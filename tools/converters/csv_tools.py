# csv, columns, transpose, delimiter, dedupe, data

from pathlib import Path
from typing import Literal
import csv


def csv_tools(
    data_file: Path,
    operation: Literal[
        "transpose",
        "keep_columns",
        "drop_columns",
        "reorder_columns",
        "rename_header",
        "remove_header",
        "remove_duplicate_rows",
        "sort_by_column",
        "change_delimiter",
    ] = "transpose",
    columns: str = "",
    delimiter: Literal["comma", "semicolon", "tab", "pipe"] = "comma",
) -> Path:
    """Reshape a CSV: transpose it, keep/drop/reorder columns (names or 1-based numbers,
    comma separated), rename the header, drop it, dedupe rows, sort by a column, or
    change the delimiter.
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(text.splitlines(), dialect=dialect) if r]
    if not rows:
        raise ValueError("The CSV is empty")
    header = rows[0]

    def indexes(spec: str) -> list[int]:
        found = []
        for part in [p.strip() for p in spec.split(",") if p.strip()]:
            if part.isdigit() and 1 <= int(part) <= len(header):
                found.append(int(part) - 1)
            elif part in header:
                found.append(header.index(part))
            else:
                raise ValueError(f"No column '{part}'. Columns: {', '.join(header)}")
        return found

    if operation == "transpose":
        width = max(len(r) for r in rows)
        rows = [[(r[i] if i < len(r) else "") for r in rows] for i in range(width)]
    elif operation in ("keep_columns", "reorder_columns"):
        keep = indexes(columns)
        rows = [[(r[i] if i < len(r) else "") for i in keep] for r in rows]
    elif operation == "drop_columns":
        drop = set(indexes(columns))
        rows = [[v for i, v in enumerate(r) if i not in drop] for r in rows]
    elif operation == "rename_header":
        rows[0] = [p.strip() for p in columns.split(",")]
    elif operation == "remove_header":
        rows = rows[1:]
    elif operation == "remove_duplicate_rows":
        rows = [header] + list(dict.fromkeys(tuple(r) for r in rows[1:]))
        rows = [list(r) for r in rows]
    elif operation == "sort_by_column":
        col = indexes(columns or "1")[0]

        def key(r):
            v = r[col] if col < len(r) else ""
            try:
                return (0, float(v), "")
            except ValueError:
                return (1, 0.0, v.lower())

        rows = [header] + sorted(rows[1:], key=key)

    out_delim = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}[delimiter]
    out = data_file.with_name(f"{data_file.stem}_{operation}.{'tsv' if delimiter == 'tab' else 'csv'}")
    with open(out, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=out_delim).writerows(rows)
    return out
