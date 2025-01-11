# sha

from pathlib import Path
from typing import Literal
import hashlib


def sha256(
    file: Path,
    hash: Literal[
        "md5",
        "sha1",
        "sha224",
        "sha256",
        "sha384",
        "sha512",
        "sha3_224",
        "sha3_256",
        "sha3_384",
        "sha3_512",
    ],
) -> str:
    hasher = getattr(hashlib, str(hash))()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
