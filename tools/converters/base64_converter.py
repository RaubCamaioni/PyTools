# text, encoding, base64, converter

from typing import Literal
import base64
import binascii


def base64_converter(
    input: str,
    mode: Literal["encode", "decode"],
    alphabet: Literal["standard", "urlsafe"],
) -> str:
    """Encode text to Base64 or decode Base64 back to text."""
    if mode == "encode":
        raw = input.encode("utf-8")
        if alphabet == "urlsafe":
            return base64.urlsafe_b64encode(raw).decode("ascii")
        return base64.b64encode(raw).decode("ascii")

    data = "".join(input.split())
    if alphabet == "urlsafe":
        data = data.replace("-", "+").replace("_", "/")
    data += "=" * (-len(data) % 4)
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as e:
        return f"Invalid Base64 input: {e}"
    return raw.decode("utf-8", errors="replace")
