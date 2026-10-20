# text, unicode, ascii, encoding, converter

from typing import Literal
import re
import unicodedata

TOKEN = re.compile(
    r"U\+([0-9A-Fa-f]+)|\\u\{?([0-9A-Fa-f]+)\}?|\\U([0-9A-Fa-f]{8})|&#x([0-9A-Fa-f]+);|&#(\d+);|0x([0-9A-Fa-f]+)|(\d+)"
)


def unicode_converter(
    input: str,
    mode: Literal["text_to_codepoints", "codepoints_to_text", "inspect"],
    format: Literal["hex", "decimal", "python_escape", "html_entity"],
) -> str:
    """Convert text to Unicode code points (U+0041, 65, \\u0041, &#65;) and back, or
    inspect each character's name.
    """
    if mode == "text_to_codepoints":
        parts = []
        for ch in input:
            cp = ord(ch)
            if format == "hex":
                parts.append(f"U+{cp:04X}")
            elif format == "decimal":
                parts.append(str(cp))
            elif format == "python_escape":
                parts.append(f"\\u{cp:04x}" if cp <= 0xFFFF else f"\\U{cp:08x}")
            else:
                parts.append(f"&#{cp};")
        return "".join(parts) if format == "html_entity" else " ".join(parts)

    if mode == "inspect":
        lines = []
        for ch in input:
            name = unicodedata.name(ch, "<unknown>")
            lines.append(f"{ch!r}  U+{ord(ch):04X}  {name}  category={unicodedata.category(ch)}")
        return "\n".join(lines)

    chars = []
    for groups in TOKEN.findall(input):
        hex_value = groups[0] or groups[1] or groups[2] or groups[3] or groups[5]
        dec_value = groups[4] or groups[6]
        try:
            chars.append(chr(int(hex_value, 16) if hex_value else int(dec_value)))
        except (ValueError, OverflowError):
            chars.append("?")
    return "".join(chars)
