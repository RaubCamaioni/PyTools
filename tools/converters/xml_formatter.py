# xml, format, minify, validate

from pathlib import Path
from typing import Literal
import xml.dom.minidom
import xml.parsers.expat
import re


def xml_formatter(
    xml_file: Path, action: Literal["pretty_print", "minify", "validate"] = "pretty_print", indent: int = 2
) -> Path:
    """Pretty-print or minify an XML file, or check that it is well-formed and report
    the line and column of the first error.
    """
    text = xml_file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dom = xml.dom.minidom.parseString(text.encode("utf-8"))
    except xml.parsers.expat.ExpatError as e:
        report = xml_file.with_name(f"{xml_file.stem}_error.txt")
        report.write_text(f"Not well-formed XML: {e}\n", encoding="utf-8")
        return report
    if action == "validate":
        report = xml_file.with_name(f"{xml_file.stem}_valid.txt")
        report.write_text(f"Well-formed XML. Root element: <{dom.documentElement.tagName}>\n", encoding="utf-8")
        return report
    if action == "minify":
        compact = re.sub(r">\s+<", "><", dom.toxml()).strip()
        out = xml_file.with_name(f"{xml_file.stem}_min.xml")
        out.write_text(compact + "\n", encoding="utf-8")
        return out
    pretty = dom.toprettyxml(indent=" " * max(0, indent))
    pretty = "\n".join(line for line in pretty.splitlines() if line.strip())
    out = xml_file.with_name(f"{xml_file.stem}_pretty.xml")
    out.write_text(pretty + "\n", encoding="utf-8")
    return out
