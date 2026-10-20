# rtf, text, document, converter

from pathlib import Path
from striprtf.striprtf import rtf_to_text as strip


def rtf_to_text(rtf_file: Path) -> Path:
    """Extract the plain text from a Rich Text Format (.rtf) document."""
    raw = rtf_file.read_text(encoding="utf-8", errors="replace")
    text = strip(raw, errors="ignore")
    out = rtf_file.with_suffix(".txt")
    out.write_text(text.strip() + "\n", encoding="utf-8")
    return out
