# json, yaml, toml, data, converter

from pathlib import Path
from typing import Literal
import json
import yaml
import tomli_w

try:
    import tomllib
except ModuleNotFoundError:  # python < 3.11
    import tomli as tomllib


def json_yaml_converter(
    data_file: Path,
    output: Literal["yaml", "json", "toml"],
) -> Path:
    """Convert between JSON, YAML and TOML. The input format is detected from the file
    extension (falls back to trying each parser).
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    suffix = data_file.suffix.lower()

    parsers = {
        ".json": lambda t: json.loads(t),
        ".yaml": lambda t: yaml.safe_load(t),
        ".yml": lambda t: yaml.safe_load(t),
        ".toml": lambda t: tomllib.loads(t),
    }
    order = [suffix] + [s for s in (".json", ".toml", ".yaml") if s != suffix]
    data = None
    errors = []
    for s in order:
        if s not in parsers:
            continue
        try:
            data = parsers[s](text)
            break
        except Exception as e:  # noqa: BLE001 - report every parser's complaint
            errors.append(f"{s}: {e}")
    else:
        raise ValueError("Could not parse input as JSON, YAML or TOML:\n" + "\n".join(errors))

    out = data_file.with_suffix("." + output)
    if output == "json":
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    elif output == "yaml":
        out.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False), encoding="utf-8"
        )
    else:
        if not isinstance(data, dict):
            raise ValueError("TOML output requires a top-level object (table), not a list or scalar")
        out.write_text(tomli_w.dumps(data), encoding="utf-8")
    return out
