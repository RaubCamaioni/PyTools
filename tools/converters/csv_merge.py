# csv, merge, join, combine, vlookup, data

from pathlib import Path
from typing import Literal
import csv


def csv_merge(
    first_csv: Path,
    second_csv: Path,
    mode: Literal["stack_rows", "join_on_key_column", "side_by_side_columns"] = "stack_rows",
    key_column: str = "id",
) -> dict:
    """Combine two CSVs: stack the rows (header matched by name), join them on a shared
    key column like a VLOOKUP (left join), or put their columns side by side row for
    row.
    """

    def read(path: Path) -> tuple[list[str], list[dict]]:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(text.splitlines(), dialect=dialect)
        rows = list(reader)
        return list(reader.fieldnames or []), rows

    header_a, rows_a = read(first_csv)
    header_b, rows_b = read(second_csv)
    if mode == "stack_rows":
        header = header_a + [h for h in header_b if h not in header_a]
        rows = rows_a + rows_b
    elif mode == "side_by_side_columns":
        header = header_a + [h if h not in header_a else f"{h}_2" for h in header_b]
        rows = []
        for i in range(max(len(rows_a), len(rows_b))):
            a = rows_a[i] if i < len(rows_a) else {}
            b = rows_b[i] if i < len(rows_b) else {}
            merged = dict(a)
            for h in header_b:
                merged[h if h not in header_a else f"{h}_2"] = b.get(h, "")
            rows.append(merged)
    else:
        key = key_column.strip()
        if key not in header_a or key not in header_b:
            return {"error": f"Both files need a '{key}' column. First: {header_a}. Second: {header_b}"}
        lookup = {r[key]: r for r in rows_b}
        header = header_a + [h for h in header_b if h not in header_a]
        rows = [{**lookup.get(r[key], {}), **r} for r in rows_a]
        matched = sum(1 for r in rows_a if r[key] in lookup)
    out = Path(f"{first_csv.stem}_{mode}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    result = {"file": out, "rows": len(rows), "columns": header}
    if mode == "join_on_key_column":
        result["rows_matched"] = matched
    return result
