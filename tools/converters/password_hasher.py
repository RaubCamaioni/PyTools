# password, hash, bcrypt, pbkdf2, scrypt, htpasswd, security

from typing import Literal
import base64
import hashlib
import secrets
import bcrypt


def password_hasher(
    password: str,
    algorithm: Literal["bcrypt", "pbkdf2_sha256", "scrypt", "sha512_crypt_like"] = "bcrypt",
    mode: Literal["hash", "verify"] = "hash",
    existing_hash: str = "",
) -> dict:
    """Hash a password the way login systems store it (bcrypt, PBKDF2-SHA256, scrypt) or
    verify a password against an existing hash. The bcrypt output is also an htpasswd
    line.
    """
    raw = password.encode("utf-8")
    if mode == "verify":
        h = existing_hash.strip()
        try:
            if h.startswith("$2"):
                ok = bcrypt.checkpw(raw, h.encode())
            elif h.startswith("pbkdf2_sha256$"):
                _, rounds, salt, digest = h.split("$")
                ok = secrets.compare_digest(_pbkdf2(raw, salt, int(rounds)), digest)
            elif h.startswith("scrypt$"):
                _, salt, digest = h.split("$")
                ok = secrets.compare_digest(_scrypt(raw, salt), digest)
            else:
                return {"error": "Unrecognised hash; expected $2b$ (bcrypt), pbkdf2_sha256$... or scrypt$..."}
        except (ValueError, TypeError) as e:
            return {"error": f"Malformed hash: {e}"}
        return {"matches": ok}

    if algorithm == "bcrypt":
        h = bcrypt.hashpw(raw[:72], bcrypt.gensalt(rounds=12)).decode()
        return {"hash": h, "htpasswd_line": f"user:{h}", "note": "bcrypt uses the first 72 bytes of the password"}
    salt = base64.b64encode(secrets.token_bytes(16)).decode().rstrip("=")
    if algorithm == "pbkdf2_sha256":
        return {"hash": f"pbkdf2_sha256$600000${salt}${_pbkdf2(raw, salt, 600000)}"}
    if algorithm == "scrypt":
        return {"hash": f"scrypt${salt}${_scrypt(raw, salt)}"}
    digest = hashlib.sha512(salt.encode() + raw).hexdigest()
    return {"hash": f"$6${salt}${digest}", "note": "a plain salted SHA-512, not glibc's crypt(3) iterated format"}


def _pbkdf2(raw: bytes, salt: str, rounds: int) -> str:
    return base64.b64encode(hashlib.pbkdf2_hmac("sha256", raw, salt.encode(), rounds)).decode()


def _scrypt(raw: bytes, salt: str) -> str:
    return base64.b64encode(hashlib.scrypt(raw, salt=salt.encode(), n=2**14, r=8, p=1, dklen=32)).decode()
