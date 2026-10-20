# text, wrap, justify, columns, format

from pathlib import Path
from typing import Literal
import textwrap


def text_wrap(
    text_file: Path,
    width: int = 80,
    style: Literal["wrap", "justify", "center", "right_align", "unwrap_paragraphs", "indent"] = "wrap",
    indent_spaces: int = 4,
) -> Path:
    """Re-flow a text file to a column width: wrap, fully justify, centre or right-align
    each paragraph, join wrapped lines back into paragraphs, or indent every line.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    width = max(10, min(width, 500))
    paragraphs = [p for p in text.replace("\r\n", "\n").split("\n\n")]
    out_paragraphs = []
    for para in paragraphs:
        flat = " ".join(para.split())
        if not flat:
            continue
        if style == "unwrap_paragraphs":
            out_paragraphs.append(flat)
        elif style == "indent":
            out_paragraphs.append("\n".join(" " * max(0, indent_spaces) + line for line in para.splitlines()))
        else:
            lines = textwrap.wrap(flat, width=width, break_long_words=False, break_on_hyphens=False)
            if style == "center":
                lines = [line.center(width).rstrip() for line in lines]
            elif style == "right_align":
                lines = [line.rjust(width) for line in lines]
            elif style == "justify":
                lines = [justify(line, width) for line in lines[:-1]] + lines[-1:]
            out_paragraphs.append("\n".join(lines))
    out = text_file.with_name(f"{text_file.stem}_{style}.txt")
    out.write_text("\n\n".join(out_paragraphs) + "\n", encoding="utf-8")
    return out


def justify(line: str, width: int) -> str:
    words = line.split()
    if len(words) < 2:
        return line
    gaps = len(words) - 1
    spaces = width - sum(len(w) for w in words)
    base, extra = divmod(spaces, gaps)
    return "".join(w + " " * (base + (1 if i < extra else 0)) for i, w in enumerate(words[:-1])) + words[-1]
