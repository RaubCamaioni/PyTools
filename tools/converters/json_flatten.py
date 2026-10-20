# json, flatten, unflatten, nested, keys, csv

from pathlib import Path
from typing import Literal
import json


def json_flatten(json_file: Path, direction: Literal["flatten", "unflatten"] = "flatten", separator: str = ".") -> Path:
    """Flatten nested JSON into dotted keys (`user.address.city`, `items[0].price`) so
    it fits a spreadsheet or config file, or rebuild the nested structure from
    flattened keys.
    """
    data = json.loads(json_file.read_text(encoding="utf-8-sig"))
    sep = separator or "."

    def flatten(value, prefix=""):
        if isinstance(value, dict) and value:
            for k, v in value.items():
                yield from flatten(v, f"{prefix}{sep}{k}" if prefix else str(k))
        elif isinstance(value, list) and value:
            for i, v in enumerate(value):
                yield from flatten(v, f"{prefix}[{i}]")
        else:
            yield prefix or "(root)", value

    def set_path(root, key, value):
        parts = []
        for piece in key.split(sep):
            head, *idx = piece.replace("]", "").split("[")
            if head:
                parts.append(head)
            parts.extend(int(i) for i in idx)
        node = root
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            nxt = parts[i + 1] if not last else None
            container = [] if isinstance(nxt, int) else {}
            if isinstance(part, int):
                while len(node) <= part:
                    node.append(None)
                if last:
                    node[part] = value
                elif node[part] is None:
                    node[part] = container
                node = node[part] if not last else node
            else:
                if last:
                    node[part] = value
                else:
                    node = node.setdefault(part, container)

    if direction == "flatten":
        result = dict(flatten(data))
    else:
        if not isinstance(data, dict):
            raise ValueError("Unflatten expects a JSON object of flat keys")
        first = next(iter(data), "")
        result = [] if first.startswith("[") else {}
        for k, v in data.items():
            set_path(result, k, v)
    out = json_file.with_name(f"{json_file.stem}_{direction}.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
