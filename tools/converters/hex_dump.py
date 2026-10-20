# hex, binary, file, inspect

from pathlib import Path
from typing import Literal


def hex_dump(file: Path, max_bytes: int = 512, output: Literal["dump", "hex_string", "base64"] = "dump") -> str:
    """Show the first bytes of any file as a classic hex dump (offset, hex, ASCII), a
    plain hex string or Base64.
    """
    import base64

    max_bytes = max(16, min(max_bytes, 65536))
    with open(file, "rb") as f:
        data = f.read(max_bytes)
    size = file.stat().st_size

    if output == "hex_string":
        body = data.hex(" ")
    elif output == "base64":
        body = base64.b64encode(data).decode("ascii")
    else:
        lines = []
        for offset in range(0, len(data), 16):
            chunk = data[offset : offset + 16]
            hexes = " ".join(f"{b:02x}" for b in chunk)
            hexes = hexes[:23] + "  " + hexes[23:] if len(chunk) > 8 else hexes
            ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{offset:08x}  {hexes:<49} |{ascii_}|")
        body = "\n".join(lines)

    header = f"{file.name}: {size} bytes" + (f" (showing first {len(data)})" if size > len(data) else "")
    return header + "\n" + body
