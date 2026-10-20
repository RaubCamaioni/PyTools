# number, binary, hex, octal, converter

from typing import Literal

PREFIXES = {"2": "0b", "8": "0o", "16": "0x"}


def number_base_converter(
    number: str,
    from_base: Literal["10", "16", "2", "8", "36"],
) -> dict:
    """Convert a number from binary, octal, decimal, hex or base 36 into all of them at once."""
    text = number.strip().replace("_", "").replace(" ", "")
    base = int(from_base)
    lower = text.lower()
    if base in (2, 8, 16) and lower.startswith(PREFIXES[str(base)]):
        text = text[2:]
    try:
        value = int(text, base)
    except ValueError:
        return {"error": f"'{number}' is not a valid base {base} number"}

    sign = "-" if value < 0 else ""
    magnitude = abs(value)

    def to_base(n: int, b: int) -> str:
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        if n == 0:
            return "0"
        out = []
        while n:
            n, r = divmod(n, b)
            out.append(digits[r])
        return "".join(reversed(out))

    return {
        "decimal": str(value),
        "binary": sign + bin(magnitude)[2:],
        "octal": sign + oct(magnitude)[2:],
        "hexadecimal": sign + hex(magnitude)[2:].upper(),
        "base36": sign + to_base(magnitude, 36).upper(),
        "binary_grouped": sign + " ".join(
            bin(magnitude)[2:].zfill((magnitude.bit_length() + 7) // 8 * 8 or 8)[i : i + 8]
            for i in range(0, (magnitude.bit_length() + 7) // 8 * 8 or 8, 8)
        ),
    }
