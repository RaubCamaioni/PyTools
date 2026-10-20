# text, lines, sort, dedupe

from pathlib import Path
from typing import Literal
import random


def line_tools(
    text_file: Path,
    operation: Literal[
        "sort",
        "sort_reverse",
        "sort_numeric",
        "sort_by_length",
        "remove_duplicates",
        "remove_empty_lines",
        "reverse_order",
        "shuffle",
        "trim_whitespace",
        "add_line_numbers",
        "lowercase",
        "uppercase",
    ],
) -> Path:
    """Sort, dedupe, reverse, shuffle, trim or number the lines of a text file."""
    lines = text_file.read_text(encoding="utf-8", errors="replace").splitlines()

    if operation == "sort":
        lines = sorted(lines, key=str.casefold)
    elif operation == "sort_reverse":
        lines = sorted(lines, key=str.casefold, reverse=True)
    elif operation == "sort_numeric":

        def key(line: str):
            try:
                return (0, float(line.strip().split()[0]))
            except (ValueError, IndexError):
                return (1, 0.0)

        lines = sorted(lines, key=key)
    elif operation == "sort_by_length":
        lines = sorted(lines, key=len)
    elif operation == "remove_duplicates":
        lines = list(dict.fromkeys(lines))
    elif operation == "remove_empty_lines":
        lines = [line for line in lines if line.strip()]
    elif operation == "reverse_order":
        lines = lines[::-1]
    elif operation == "shuffle":
        random.shuffle(lines)
    elif operation == "trim_whitespace":
        lines = [line.strip() for line in lines]
    elif operation == "add_line_numbers":
        width = len(str(len(lines)))
        lines = [f"{i:>{width}}  {line}" for i, line in enumerate(lines, 1)]
    elif operation == "lowercase":
        lines = [line.lower() for line in lines]
    elif operation == "uppercase":
        lines = [line.upper() for line in lines]

    output = text_file.with_name(f"{text_file.stem}_{operation}.txt")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
