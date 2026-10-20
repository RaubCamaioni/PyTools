# xml, json, data, converter

from pathlib import Path
from typing import Literal
import json
import xmltodict


def xml_json_converter(data_file: Path, output: Literal["json", "xml"], root_name: str = "root") -> Path:
    """Convert XML to JSON or JSON to XML. Attributes become "@name" keys and text
    becomes "#text" (xmltodict convention).
    """
    text = data_file.read_text(encoding="utf-8-sig", errors="replace")
    out = data_file.with_suffix("." + output)

    if output == "json":
        data = xmltodict.parse(text)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return out

    data = json.loads(text)
    root = root_name.strip() or "root"
    if isinstance(data, list):
        data = {root: {"item": data}}
    elif not (isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), (dict, str))):
        data = {root: data}
    out.write_text(xmltodict.unparse(data, pretty=True, indent="  ") + "\n", encoding="utf-8")
    return out
