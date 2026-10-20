# totp, 2fa, otp, authenticator, security

from pathlib import Path
from typing import Literal
import base64
import hashlib
import hmac
import secrets
import struct
import time
import qrcode


def totp_generator(
    action: Literal["new_secret", "current_code"] = "new_secret",
    secret: str = "",
    account: str = "user@example.com",
    issuer: str = "PyTools",
    digits: int = 6,
    period: int = 30,
) -> dict:
    """Create a new authenticator secret (with the otpauth:// URI and a QR code to scan)
    or compute the current time-based one-time code for an existing Base32 secret,
    RFC 6238 style.
    """
    digits = 8 if digits >= 8 else 6
    period = max(15, min(period, 120))
    if action == "new_secret":
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
    key_text = secret.strip().replace(" ", "").upper()
    try:
        key = base64.b32decode(key_text + "=" * (-len(key_text) % 8))
    except Exception:  # noqa: BLE001
        return {"error": "The secret must be Base32 (letters A-Z and digits 2-7)"}

    counter = int(time.time()) // period
    codes = []
    for offset in (-1, 0, 1):
        mac = hmac.new(key, struct.pack(">Q", counter + offset), hashlib.sha1).digest()
        start = mac[-1] & 0x0F
        value = (struct.unpack(">I", mac[start : start + 4])[0] & 0x7FFFFFFF) % (10**digits)
        codes.append(str(value).zfill(digits))
    result = {
        "secret_base32": key_text,
        "current_code": codes[1],
        "previous_and_next": [codes[0], codes[2]],
        "seconds_until_next": period - int(time.time()) % period,
    }
    if action == "new_secret":
        uri = f"otpauth://totp/{issuer}:{account}?secret={key_text}&issuer={issuer}&digits={digits}&period={period}"
        out = Path("totp_qr.png")
        qrcode.make(uri).save(out)
        result.update({"otpauth_uri": uri, "qr_code": out})
    return result
