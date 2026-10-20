# json, diff, compare, data

from pathlib import Path
import json


def json_diff(original: Path, modified: Path, max_changes: int = 500) -> dict:
    """Compare two JSON files structurally (order of keys ignored) and list every added,
    removed and changed value with its path, such as users[2].email.
    """
    a = json.loads(original.read_text(encoding="utf-8-sig"))
    b = json.loads(modified.read_text(encoding="utf-8-sig"))
    added, removed, changed = [], [], []

    def walk(x, y, path):
        if len(added) + len(removed) + len(changed) >= max_changes:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for k in x.keys() | y.keys():
                p = f"{path}.{k}" if path else str(k)
                if k not in y:
                    removed.append({"path": p, "value": x[k]})
                elif k not in x:
                    added.append({"path": p, "value": y[k]})
                else:
                    walk(x[k], y[k], p)
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                p = f"{path}[{i}]"
                if i >= len(y):
                    removed.append({"path": p, "value": x[i]})
                elif i >= len(x):
                    added.append({"path": p, "value": y[i]})
                else:
                    walk(x[i], y[i], p)
        elif x != y or type(x) is not type(y):
            changed.append({"path": path or "(root)", "from": x, "to": y})

    walk(a, b, "")
    return {
        "identical": not (added or removed or changed),
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": f"{len(added)} added, {len(removed)} removed, {len(changed)} changed",
    }
