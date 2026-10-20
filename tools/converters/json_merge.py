# json, merge, combine, deep merge, config

from pathlib import Path
from typing import Literal
import json


def json_merge(
    base_json: Path,
    overlay_json: Path,
    strategy: Literal["deep_merge", "overlay_wins", "concatenate_arrays"] = "deep_merge",
) -> Path:
    """Merge two JSON files: deep-merge objects (the overlay's values win on conflicts),
    simply overlay top-level keys, or concatenate when both are arrays.
    """
    a = json.loads(base_json.read_text(encoding="utf-8-sig"))
    b = json.loads(overlay_json.read_text(encoding="utf-8-sig"))

    def deep(x, y):
        if isinstance(x, dict) and isinstance(y, dict):
            merged = dict(x)
            for k, v in y.items():
                merged[k] = deep(x[k], v) if k in x else v
            return merged
        if isinstance(x, list) and isinstance(y, list) and strategy == "concatenate_arrays":
            return x + y
        return y

    if strategy == "overlay_wins" and isinstance(a, dict) and isinstance(b, dict):
        result = {**a, **b}
    elif isinstance(a, list) and isinstance(b, list):
        result = a + b
    else:
        result = deep(a, b)
    out = Path(f"{base_json.stem}_merged.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
