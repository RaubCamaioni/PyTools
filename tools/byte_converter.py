from pyparsing import Word, hexnums, Optional, Combine, OneOrMore
from typing import Literal


def string_to_bytes(input: str) -> str:
    bytes = [f"0x{ord(char):02X}" for char in input]
    return " ".join(bytes)


def bytes_to_string(input: str) -> str:
    hex_parser = OneOrMore(Combine(Optional("0x") + Word(hexnums)))
    result = hex_parser.searchString(input)
    bytes = (int(h, 16) for sublist in result for h in sublist)
    return "".join(chr(b) for b in bytes)


def byte_converter(input: str, output: Literal["hexadecimal", "string"]) -> str:
    if output == "hexadecimal":
        return string_to_bytes(input)
    elif output == "string":
        return bytes_to_string(input)
    else:
        raise ValueError("output not defined")
