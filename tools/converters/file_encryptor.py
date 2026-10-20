# encrypt, decrypt, aes, password, file, security

from pathlib import Path
from typing import Literal
import secrets
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"PYTENC1\0"
ROUNDS = 600_000


def file_encryptor(file: Path, password: str, action: Literal["encrypt", "decrypt"] = "encrypt") -> dict:
    """Encrypt any file with a password (AES-256-GCM, key from PBKDF2-SHA256) into a
    .enc file, or decrypt a .enc file made here. A wrong password is detected rather
    than producing garbage.
    """
    if not password:
        return {"error": "A password is required"}
    data = file.read_bytes()
    if action == "encrypt":
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        key = _key(password, salt)
        body = AESGCM(key).encrypt(nonce, data, file.name.encode())
        out = file.with_name(file.name + ".enc")
        name = file.name.encode()
        out.write_bytes(MAGIC + salt + nonce + len(name).to_bytes(2, "big") + name + body)
        return {"file": out, "bytes": out.stat().st_size, "cipher": "AES-256-GCM, PBKDF2-SHA256 600k rounds"}

    if not data.startswith(MAGIC):
        return {"error": "This is not a file encrypted by this tool"}
    salt, nonce = data[8:24], data[24:36]
    name_len = int.from_bytes(data[36:38], "big")
    name = data[38 : 38 + name_len]
    body = data[38 + name_len :]
    try:
        plain = AESGCM(_key(password, salt)).decrypt(nonce, body, name)
    except InvalidTag:
        return {"error": "Wrong password (or the file is damaged)"}
    out = Path(name.decode(errors="replace") or file.stem)
    if out.suffix == ".enc":
        out = out.with_suffix("")
    out.write_bytes(plain)
    return {"file": out, "bytes": len(plain)}


def _key(password: str, salt: bytes) -> bytes:
    return PBKDF2HMAC(hashes.SHA256(), 32, salt, ROUNDS).derive(password.encode("utf-8"))
