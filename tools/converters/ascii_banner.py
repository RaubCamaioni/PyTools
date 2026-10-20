# text, ascii, art, banner, figlet, generator

from typing import Literal
import pyfiglet


def ascii_banner(
    text: str = "Hello",
    font: Literal[
        "standard", "slant", "big", "small", "banner", "block", "doom", "digital", "bubble", "script"
    ] = "standard",
) -> str:
    """Render text as a large ASCII-art banner (figlet fonts), for READMEs, terminals
    and signatures.
    """
    return pyfiglet.figlet_format(text[:60], font=font, width=200)
