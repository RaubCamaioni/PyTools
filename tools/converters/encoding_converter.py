# text, encoding, base32, base58, ascii85, punycode, uuencode, converter

from typing import Literal
import base64
import binascii

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_encode(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    out = ""
    while number:
        number, rest = divmod(number, 58)
        out = BASE58[rest] + out
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + out


def base58_decode(text: str) -> bytes:
    number = 0
    for ch in text.strip():
        number = number * 58 + BASE58.index(ch)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\0" * (len(text) - len(text.lstrip("1"))) + raw


def encoding_converter(
    input: str,
    encoding: Literal["base32", "base58", "ascii85", "base85", "uuencode", "punycode", "hex"],
    mode: Literal["encode", "decode"],
) -> str:
    """Encode text with Base32, Base58, Ascii85, Base85, uuencode, Punycode (IDN
    domains) or hex, or decode it back to text.
    """
    try:
        if mode == "encode":
            raw = input.encode("utf-8")
            if encoding == "base32":
                return base64.b32encode(raw).decode()
            if encoding == "base58":
                return base58_encode(raw)
            if encoding == "ascii85":
                return base64.a85encode(raw).decode()
            if encoding == "base85":
                return base64.b85encode(raw).decode()
            if encoding == "uuencode":
                return binascii.b2a_uu(raw[:45]).decode() if len(raw) <= 45 else "uuencode takes at most 45 bytes"
            if encoding == "punycode":
                return ".".join(label.encode("idna").decode() for label in input.strip().split("."))
            return raw.hex()

        text = input.strip()
        if encoding == "base32":
            raw = base64.b32decode(text.upper() + "=" * (-len(text) % 8))
        elif encoding == "base58":
            raw = base58_decode(text)
        elif encoding == "ascii85":
            raw = base64.a85decode(text)
        elif encoding == "base85":
            raw = base64.b85decode(text)
        elif encoding == "uuencode":
            raw = binascii.a2b_uu(text)
        elif encoding == "punycode":
            return ".".join(label.encode("ascii").decode("idna") for label in text.split("."))
        else:
            raw = bytes.fromhex("".join(text.split()))
        return raw.decode("utf-8", errors="replace")
    except (ValueError, binascii.Error, UnicodeError) as e:
        return f"Invalid {encoding} input: {e}"
