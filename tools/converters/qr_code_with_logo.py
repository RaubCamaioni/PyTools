# qr, code, logo, brand, image, generator

from pathlib import Path
import re
import qrcode
from PIL import Image


def qr_code_with_logo(
    logo: Path, text: str = "https://pywebtools.com", foreground: str = "#000000", size: int = 600
) -> Path:
    """A QR code with your logo or picture in the middle. Error correction is set to the
    highest level so the code still scans with the centre covered.
    """
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", foreground.strip())
    fg = tuple(int(m.group(1)[i : i + 2], 16) for i in (0, 2, 4)) if m else (0, 0, 0)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=12)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg, back_color=(255, 255, 255)).convert("RGBA")
    with Image.open(logo) as lg:
        lg = lg.convert("RGBA")
        side = img.width // 4
        lg.thumbnail((side, side), Image.LANCZOS)
        pad = Image.new("RGBA", (lg.width + 16, lg.height + 16), (255, 255, 255, 255))
        pad.paste(lg, (8, 8), lg)
    img.paste(pad, ((img.width - pad.width) // 2, (img.height - pad.height) // 2), pad)
    size = max(100, min(size, 2000))
    out = Path("qr_with_logo.png")
    img.convert("RGB").resize((size, size), Image.LANCZOS).save(out)
    return out
