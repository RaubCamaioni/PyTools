# wifi, qr, code, network, generator

from pathlib import Path
from typing import Literal
import qrcode


def wifi_qr_code(
    network_name: str,
    password: str = "",
    security: Literal["WPA", "WEP", "nopass"] = "WPA",
    hidden: Literal["no", "yes"] = "no",
) -> dict:
    """Make the QR code phones scan to join a Wi-Fi network: point the camera at it and
    the phone offers to connect, no typing. The password is embedded in the code and
    in nothing else.
    """

    def esc(s: str) -> str:
        return "".join("\\" + c if c in '\\;,":' else c for c in s)

    payload = (
        f"WIFI:T:{security};S:{esc(network_name)};"
        + (f"P:{esc(password)};" if security != "nopass" else "")
        + ("H:true;" if hidden == "yes" else "")
        + ";"
    )
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2, box_size=10)
    qr.add_data(payload)
    qr.make(fit=True)
    out = Path("wifi_qr.png")
    qr.make_image(fill_color="black", back_color="white").save(out)
    return {"file": out, "network": network_name, "security": security, "note": "print it and stick it on the fridge"}
