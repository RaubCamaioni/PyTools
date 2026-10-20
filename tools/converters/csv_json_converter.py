# csv, json, data, converter

from pathlib import Path
from typing import Literal
import csv
import json


def csv_json_converter(
    data_file: Path,
    output: Literal["json", "csv", "tsv"],
    numbers: Literal["convert", "keep_as_text"],
) -> Path:
    """Convert CSV/TSV to JSON (list of objects) or JSON (list of objects) to CSV/TSV.
    Delimiters are auto-detected.
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")

    def coerce(value: str):
        if numbers == "keep_as_text":
            return value
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value

    if output == "json":
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
        rows = [{k: coerce(v) for k, v in row.items()} for row in rows]
        out = data_file.with_suffix(".json")
        out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return out

    data = json.loads(text)
    if isinstance(data, dict):
        # a dict of lists (columns) or a single record
        if data and all(isinstance(v, list) for v in data.values()):
            keys = list(data)
            data = [dict(zip(keys, values)) for values in zip(*data.values())]
        else:
            data = [data]
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError("JSON must be a list of objects (or an object of lists) to become a table")

    fieldnames: list[str] = []
    for row in data:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    out = data_file.with_suffix("." + output)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t" if output == "tsv" else ",")
        writer.writeheader()
        for row in data:
            writer.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in row.items()})
    return out
