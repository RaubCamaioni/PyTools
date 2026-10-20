# qr, code, image, generator

from pathlib import Path
from typing import Literal
import qrcode
import qrcode.constants
import qrcode.image.svg


def qr_code_generator(
    text: str = "https://pywebtools.com",
    size: int = 400,
    error_correction: Literal["medium", "low", "quartile", "high"] = "medium",
    output: Literal["png", "svg"] = "png",
) -> Path:
    """Generate a QR code image for a URL, text, Wi-Fi string
    (WIFI:T:WPA;S:name;P:pass;;) or contact card.
    """
    levels = {
        "low": qrcode.constants.ERROR_CORRECT_L,
        "medium": qrcode.constants.ERROR_CORRECT_M,
        "quartile": qrcode.constants.ERROR_CORRECT_Q,
        "high": qrcode.constants.ERROR_CORRECT_H,
    }
    qr = qrcode.QRCode(error_correction=levels[error_correction], border=2, box_size=10)
    qr.add_data(text)
    qr.make(fit=True)

    if output == "svg":
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        out = Path("qr_code.svg")
        img.save(str(out))
        return out

    img = qr.make_image(fill_color="black", back_color="white").get_image()
    size = max(64, min(size, 2000))
    img = img.resize((size, size), resample=0)
    out = Path("qr_code.png")
    img.save(out)
    return out
