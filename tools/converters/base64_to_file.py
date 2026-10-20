# base64, file, image, decode, converter

from pathlib import Path
import base64
import binascii
import re

SIGNATURES = [
    (b"\x89PNG", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif"), (b"RIFF", ".webp"), (b"%PDF", ".pdf"),
    (b"BM", ".bmp"), (b"PK\x03\x04", ".zip"), (b"\x1f\x8b", ".gz"), (b"ID3", ".mp3"), (b"OggS", ".ogg"), (b"<svg", ".svg"),
    (b"<?xml", ".xml"), (b"{", ".json"), (b"II*\x00", ".tif"), (b"MM\x00*", ".tif"),
]


def base64_to_file(base64_text: Path, file_name: str = "decoded") -> Path:
    """Decode Base64 (raw or a data:...;base64, URI, pasted into a text file) back into the original file. The file type is detected from the data: URI or the bytes."""
    text = base64_text.read_text(encoding="utf-8", errors="ignore").strip()
    ext = ""
    if m := re.match(r"data:([\w/+.-]+);base64,", text):
        mime = m.group(1)
        ext = "." + {"image/jpeg": "jpg", "image/svg+xml": "svg", "text/plain": "txt"}.get(mime, mime.split("/")[-1])
        text = text[m.end():]
    text = re.sub(r"\s+", "", text)
    text += "=" * (-len(text) % 4)
    try:
        data = base64.b64decode(text, validate=False)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"Not valid Base64: {e}")
    if not ext:
        ext = next((e for sig, e in SIGNATURES if data.startswith(sig)), ".bin")
    name = Path(file_name).name or "decoded"
    out = Path(name if Path(name).suffix else name + ext)
    out.write_bytes(data)
    return out
