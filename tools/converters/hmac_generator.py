# hmac, hash, signature, security

from typing import Literal
import base64
import hashlib
import hmac


def hmac_generator(
    message: str,
    secret_key: str,
    algorithm: Literal["sha256", "sha1", "sha512", "md5", "sha3_256"] = "sha256",
    verify_against: str = "",
) -> dict:
    """Compute an HMAC signature of a message with a secret key (hex and Base64), and
    optionally check it against an expected signature using a constant-time
    comparison.
    """
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), getattr(hashlib, algorithm)).digest()
    result = {
        "algorithm": f"HMAC-{algorithm.upper()}",
        "hex": digest.hex(),
        "base64": base64.b64encode(digest).decode(),
    }
    if verify_against.strip():
        expected = verify_against.strip()
        result["verified"] = hmac.compare_digest(digest.hex().lower(), expected.lower()) or hmac.compare_digest(
            result["base64"], expected
        )
    return result
