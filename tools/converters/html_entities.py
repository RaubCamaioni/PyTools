# text, html, encoding, converter

from typing import Literal
import html


def html_entities(input: str, mode: Literal["escape", "unescape"]) -> str:
    """Escape text for HTML (& < > " ') or decode HTML entities back to text."""
    if mode == "escape":
        return html.escape(input, quote=True)
    return html.unescape(input)
