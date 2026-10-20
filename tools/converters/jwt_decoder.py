# jwt, token, decode, json

from datetime import datetime, timezone
import base64
import json


def jwt_decoder(token: str) -> dict:
    """Decode a JSON Web Token's header and payload (no signature verification) and
    explain the standard time claims.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        return {"error": "A JWT has three dot-separated parts: header.payload.signature"}

    def decode(segment: str):
        segment += "=" * (-len(segment) % 4)
        raw = base64.urlsafe_b64decode(segment)
        return json.loads(raw)

    try:
        header = decode(parts[0])
        payload = decode(parts[1])
    except (ValueError, json.JSONDecodeError) as e:
        return {"error": f"Could not decode token: {e}"}

    now = datetime.now(timezone.utc)
    times = {}
    for claim in ("iat", "exp", "nbf"):
        value = payload.get(claim)
        if isinstance(value, (int, float)):
            when = datetime.fromtimestamp(value, timezone.utc)
            times[claim] = when.isoformat()
    if "exp" in times:
        times["expired"] = payload["exp"] < now.timestamp()

    return {
        "header": header,
        "payload": payload,
        "times": times,
        "signature_bytes": len(base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))),
        "note": "Signature was NOT verified.",
    }
