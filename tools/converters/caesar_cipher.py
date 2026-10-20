# text, cipher, rot13, converter

from typing import Literal


def caesar_cipher(input: str, shift: int = 13, mode: Literal["encode", "decode"] = "encode") -> str:
    """Shift letters by N positions (ROT13 by default). Decode shifts the other way."""
    shift = shift % 26
    if mode == "decode":
        shift = -shift
    out = []
    for ch in input:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)
