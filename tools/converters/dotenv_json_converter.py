# env, dotenv, json, yaml, config, converter

from pathlib import Path
from typing import Literal
import json
import re
import shlex
import yaml


def dotenv_json_converter(
    file: Path, output: Literal["json", "yaml", "dotenv", "shell_export", "docker_compose_environment"] = "json"
) -> Path:
    """Convert between .env files (KEY=value lines), JSON, YAML, `export KEY=value`
    shell lines and a docker-compose `environment:` block. The input format is
    detected.
    """
    text = file.read_text(encoding="utf-8-sig", errors="replace")
    data = None
    stripped = text.strip()
    if stripped.startswith("{"):
        data = json.loads(stripped)
    elif file.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(stripped)
    else:
        data = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line = re.sub(r"^export\s+", "", line)
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip()
            if value[:1] in "\"'" and value[-1:] == value[:1]:
                value = value[1:-1]
            data[key.strip()] = value
    if isinstance(data, dict) and "environment" in data and isinstance(data["environment"], (dict, list)):
        env = data["environment"]
        data = env if isinstance(env, dict) else dict(item.split("=", 1) for item in env if "=" in item)
    if not isinstance(data, dict):
        raise ValueError("Expected a flat object of KEY: value pairs")
    flat = {str(k): ("" if v is None else str(v)) for k, v in data.items()}

    if output == "json":
        content, ext = json.dumps(flat, indent=2) + "\n", "json"
    elif output == "yaml":
        content, ext = yaml.safe_dump(flat, sort_keys=False), "yaml"
    elif output == "shell_export":
        content, ext = "".join(f"export {k}={shlex.quote(v)}\n" for k, v in flat.items()), "sh"
    elif output == "docker_compose_environment":
        content, ext = "environment:\n" + "".join(f"  {k}: {json.dumps(v)}\n" for k, v in flat.items()), "yaml"
    else:
        content, ext = (
            "".join(f"{k}={v if re.fullmatch(r'[A-Za-z0-9_./:@-]*', v) else json.dumps(v)}\n" for k, v in flat.items()),
            "env",
        )
    out = file.with_name(f"{file.stem}_converted.{ext}" if ext != "env" else ".env.converted")
    out.write_text(content, encoding="utf-8")
    return out
