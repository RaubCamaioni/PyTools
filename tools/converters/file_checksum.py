# file, checksum, hash, verify, sha256, md5

from pathlib import Path
import hashlib
import zlib


def file_checksum(file: Path, expected: str = "") -> dict:
    """Compute MD5, SHA-1, SHA-256, SHA-512, BLAKE2b and CRC32 of a file at once, and
    check them against an expected hash if you paste one.
    """
    hashers = {name: hashlib.new(name) for name in ("md5", "sha1", "sha256", "sha512", "blake2b")}
    crc = 0
    size = 0
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            size += len(chunk)
            crc = zlib.crc32(chunk, crc)
            for h in hashers.values():
                h.update(chunk)
    result = {"file": file.name, "size_bytes": size}
    result.update({name: h.hexdigest() for name, h in hashers.items()})
    result["crc32"] = f"{crc & 0xFFFFFFFF:08x}"
    if expected.strip():
        wanted = expected.strip().lower()
        match = next((name for name, value in result.items() if isinstance(value, str) and value == wanted), None)
        result["verification"] = (
            f"MATCH ({match})" if match else "NO MATCH: the expected hash does not equal any digest of this file"
        )
    return result
