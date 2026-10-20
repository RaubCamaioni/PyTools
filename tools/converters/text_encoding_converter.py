# text, encoding, utf8, latin1, line endings, bom, converter

from pathlib import Path
from typing import Literal

ENCODINGS = {"utf8": "utf-8", "utf8_with_bom": "utf-8-sig", "utf16": "utf-16", "latin1": "latin-1", "windows1252": "cp1252", "ascii": "ascii"}


def text_encoding_converter(
    text_file: Path,
    output_encoding: Literal["utf8", "utf8_with_bom", "utf16", "latin1", "windows1252", "ascii"] = "utf8",
    line_endings: Literal["keep", "unix_LF", "windows_CRLF", "classic_mac_CR"] = "keep",
    input_encoding: str = "auto",
) -> dict:
    """Re-encode a text file (UTF-8 with/without BOM, UTF-16, Latin-1, Windows-1252, ASCII) and normalise its line endings; the source encoding is auto-detected."""
    raw = text_file.read_bytes()
    detected = None
    if input_encoding.strip().lower() != "auto":
        text = raw.decode(input_encoding.strip())
        detected = input_encoding
    else:
        for candidate in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
            try:
                text = raw.decode(candidate)
                if candidate == "utf-16" and not (raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff")):
                    continue
                detected = candidate
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("latin-1")
            detected = "latin-1"

    crlf, lf_only, cr_only = text.count("\r\n"), text.count("\n") - text.count("\r\n"), text.count("\r") - text.count("\r\n")
    if line_endings != "keep":
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\n", {"unix_LF": "\n", "windows_CRLF": "\r\n", "classic_mac_CR": "\r"}[line_endings])

    target = ENCODINGS[output_encoding]
    out = text_file.with_name(f"{text_file.stem}_{output_encoding}{text_file.suffix or '.txt'}")
    lost = 0
    try:
        data = text.encode(target)
    except UnicodeEncodeError:
        data = text.encode(target, errors="replace")
        lost = sum(1 for ch in text if not ch.encode(target, errors="ignore"))
    out.write_bytes(data)
    return {
        "file": out,
        "detected_input_encoding": detected,
        "input_line_endings": {"CRLF": crlf, "LF": lf_only, "CR": cr_only},
        "characters": len(text),
        "characters_replaced_with_question_marks": lost,
    }
