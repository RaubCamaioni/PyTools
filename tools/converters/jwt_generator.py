# jwt, token, sign, hs256, security

from pathlib import Path
from typing import Literal
import base64
import hashlib
import hmac
import json
import time


def jwt_generator(
    payload_json: Path,
    secret: str,
    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256",
    expires_in_minutes: int = 60,
) -> dict:
    """Sign a JSON payload into a JWT with a shared secret (HMAC). iat and exp are added
    unless the payload already has them; set expires_in_minutes to 0 for no expiry.
    """
    try:
        payload = json.loads(payload_json.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"error": f"Payload is not valid JSON: {e}"}
    if not isinstance(payload, dict):
        return {"error": "The payload must be a JSON object"}
    now = int(time.time())
    payload.setdefault("iat", now)
    if expires_in_minutes > 0:
        payload.setdefault("exp", now + expires_in_minutes * 60)

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": algorithm, "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps(payload, separators=(",", ":")).encode())
    digest = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}[algorithm]
    signature = b64(hmac.new(secret.encode(), f"{header}.{body}".encode(), digest).digest())
    return {"token": f"{header}.{body}.{signature}", "payload": payload, "algorithm": algorithm}
