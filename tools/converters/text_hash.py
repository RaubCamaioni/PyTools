# hash, md5, sha, text, checksum

from typing import Literal
import hashlib
import zlib


def text_hash(
    input: str,
    algorithm: Literal["all", "md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b", "crc32"],
) -> dict:
    """Hash a string with MD5, SHA-1, SHA-256, SHA-512, SHA3, BLAKE2 or CRC32 (or all at
    once).
    """
    data = input.encode("utf-8")
    names = ["md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b", "crc32"] if algorithm == "all" else [algorithm]
    out = {}
    for name in names:
        if name == "crc32":
            out[name] = f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"
        else:
            out[name] = hashlib.new(name, data).hexdigest()
    out["input_bytes"] = len(data)
    return out
