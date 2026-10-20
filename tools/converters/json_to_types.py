# json, typescript, python, dataclass, pydantic, types, generator

from pathlib import Path
from typing import Literal
import json
import re


def json_to_types(
    json_file: Path,
    language: Literal["typescript", "python_dataclass", "pydantic", "go_struct"] = "typescript",
    root_name: str = "Root",
) -> Path:
    """Generate type definitions from a JSON sample: TypeScript interfaces, Python
    dataclasses, Pydantic models or Go structs, one per nested object.
    """
    data = json.loads(json_file.read_text(encoding="utf-8-sig"))
    types: dict[str, dict[str, str]] = {}

    def pascal(name: str) -> str:
        return "".join(p.capitalize() for p in re.split(r"[^A-Za-z0-9]+", name) if p) or "Item"

    def type_of(value, hint: str) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if value is None:
            return "null"
        if isinstance(value, list):
            inner = {type_of(v, hint) for v in value} or {"any"}
            return f"list<{'|'.join(sorted(inner))}>"
        name = pascal(hint)
        while name in types and types[name] != {k: type_of(v, k) for k, v in value.items()}:
            name += "_"
        types.setdefault(name, {k: type_of(v, k) for k, v in value.items()})
        return name

    root = type_of(data, root_name)

    def render(t: str) -> str:
        if t.startswith("list<"):
            inner = render(t[5:-1].split("|")[0]) if "|" not in t[5:-1] else "any"
            return {
                "typescript": f"{inner}[]",
                "python_dataclass": f"list[{inner}]",
                "pydantic": f"list[{inner}]",
                "go_struct": f"[]{inner}",
            }[language]
        table = {
            "typescript": {
                "boolean": "boolean",
                "integer": "number",
                "number": "number",
                "string": "string",
                "null": "null",
                "any": "any",
            },
            "python_dataclass": {
                "boolean": "bool",
                "integer": "int",
                "number": "float",
                "string": "str",
                "null": "None",
                "any": "Any",
            },
            "pydantic": {
                "boolean": "bool",
                "integer": "int",
                "number": "float",
                "string": "str",
                "null": "None",
                "any": "Any",
            },
            "go_struct": {
                "boolean": "bool",
                "integer": "int64",
                "number": "float64",
                "string": "string",
                "null": "any",
                "any": "any",
            },
        }[language]
        return table.get(t, t)

    lines = []
    if language == "python_dataclass":
        lines += ["from dataclasses import dataclass", "from typing import Any", ""]
    elif language == "pydantic":
        lines += ["from typing import Any", "from pydantic import BaseModel", ""]
    elif language == "go_struct":
        lines += ["package main", ""]
    for name, fields in reversed(list(types.items())):
        if language == "typescript":
            lines.append(f"export interface {name} {{")
            lines += [f"  {k}: {render(t)};" for k, t in fields.items()]
            lines.append("}")
        elif language == "go_struct":
            lines.append(f"type {name} struct {{")
            lines += [f'\t{pascal(k)} {render(t)} `json:"{k}"`' for k, t in fields.items()]
            lines.append("}")
        else:
            lines.append("@dataclass" if language == "python_dataclass" else "")
            lines.append(f"class {name}{'' if language == 'python_dataclass' else '(BaseModel)'}:")
            lines += [f"    {re.sub(r'[^A-Za-z0-9_]', '_', k)}: {render(t)}" for k, t in fields.items()] or ["    pass"]
        lines.append("")
    if not types:
        lines.append(f"// top level is {render(root)}")
    ext = {"typescript": "ts", "python_dataclass": "py", "pydantic": "py", "go_struct": "go"}[language]
    out = json_file.with_name(f"{json_file.stem}_types.{ext}")
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return out
