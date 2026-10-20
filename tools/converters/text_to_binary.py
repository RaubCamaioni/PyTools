# text, binary, encoding, converter

from typing import Literal


def text_to_binary(
    input: str,
    mode: Literal["text_to_binary", "binary_to_text"],
) -> str:
    """Convert text to space-separated 8-bit binary (UTF-8 bytes) and back."""
    if mode == "text_to_binary":
        return " ".join(f"{b:08b}" for b in input.encode("utf-8"))

    bits = "".join(ch for ch in input if ch in "01")
    if not bits or len(bits) % 8:
        return "Binary input must be a multiple of 8 bits (0 and 1 only, spaces allowed)."
    data = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))
    return data.decode("utf-8", errors="replace")
