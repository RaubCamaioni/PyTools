# text, case, converter

from typing import Literal
import re


def _words(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return [w for w in re.split(r"[^A-Za-z0-9]+", text) if w]


def text_case_converter(
    input: str,
    case: Literal[
        "UPPERCASE",
        "lowercase",
        "Title_Case",
        "Sentence_case",
        "snake_case",
        "camelCase",
        "PascalCase",
        "kebab_case",
        "CONSTANT_CASE",
        "dot.case",
        "aLtErNaTiNg",
        "iNVERSE",
    ],
) -> str:
    """Convert text between upper, lower, title, sentence, snake, camel, pascal, kebab
    and more.
    """
    words = _words(input)
    if case == "UPPERCASE":
        return input.upper()
    if case == "lowercase":
        return input.lower()
    if case == "Title_Case":
        return input.title()
    if case == "Sentence_case":
        lowered = input.lower()
        return re.sub(r"(^\s*\w|[.!?]\s+\w)", lambda m: m.group(0).upper(), lowered)
    if case == "snake_case":
        return "_".join(w.lower() for w in words)
    if case == "camelCase":
        return "".join(w.lower() if i == 0 else w.capitalize() for i, w in enumerate(words))
    if case == "PascalCase":
        return "".join(w.capitalize() for w in words)
    if case == "kebab_case":
        return "-".join(w.lower() for w in words)
    if case == "CONSTANT_CASE":
        return "_".join(w.upper() for w in words)
    if case == "dot.case":
        return ".".join(w.lower() for w in words)
    if case == "aLtErNaTiNg":
        return "".join(c.lower() if i % 2 == 0 else c.upper() for i, c in enumerate(input))
    if case == "iNVERSE":
        return input.swapcase()
    raise ValueError(f"unknown case: {case}")
