# csv, split, chunks, data

from pathlib import Path
from typing import Literal
import csv
import zipfile


def csv_split(
    data_file: Path,
    mode: Literal["rows_per_file", "number_of_files", "by_column_value"] = "rows_per_file",
    value: str = "1000",
) -> dict:
    """Split a big CSV into smaller files (zipped), each keeping the header: every N
    rows, into N files, or one file per distinct value of a column (name or 1-based
    number).
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(text.splitlines(), dialect=dialect) if r]
    if len(rows) < 2:
        return {"error": "Nothing to split: the CSV needs a header and at least one row"}
    header, body = rows[0], rows[1:]

    parts: dict[str, list[list[str]]] = {}
    if mode == "rows_per_file":
        size = max(1, int(value))
        for i in range(0, len(body), size):
            parts[f"part_{i // size + 1:03d}"] = body[i : i + size]
    elif mode == "number_of_files":
        n = max(1, min(int(value), len(body)))
        size = -(-len(body) // n)
        for i in range(n):
            parts[f"part_{i + 1:03d}"] = body[i * size : (i + 1) * size]
    else:
        col = int(value) - 1 if value.strip().isdigit() else header.index(value.strip())
        for r in body:
            key = (r[col] if col < len(r) else "").strip() or "empty"
            safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in key)[:60]
            parts.setdefault(safe, []).append(r)

    out = data_file.with_name(f"{data_file.stem}_split.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, chunk in parts.items():
            import io

            buf = io.StringIO()
            writer = csv.writer(buf, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(chunk)
            zf.writestr(f"{data_file.stem}_{name}.csv", buf.getvalue())
    return {"file": out, "files": len(parts), "rows": len(body)}
