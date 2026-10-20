# qr, code, styled, color, rounded, generator

from pathlib import Path
from typing import Literal
import re
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    GappedSquareModuleDrawer,
)
from PIL import Image


def qr_code_styled(
    text: str = "https://pywebtools.com",
    dot_style: Literal["square", "rounded", "circle", "gapped"] = "rounded",
    foreground: str = "#1a1a2e",
    background: str = "#ffffff",
    size: int = 600,
) -> Path:
    """A QR code with style: rounded or circular dots and custom colours. For a logo in
    the middle use the qr_code_with_logo tool.
    """

    def parse(color: str, default: tuple) -> tuple:
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", color.strip())
        return (int(m.group(1)[0:2], 16), int(m.group(1)[2:4], 16), int(m.group(1)[4:6], 16)) if m else default

    fg, bg = parse(foreground, (0, 0, 0)), parse(background, (255, 255, 255))
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=12)
    qr.add_data(text)
    qr.make(fit=True)
    drawer = {
        "square": SquareModuleDrawer,
        "rounded": RoundedModuleDrawer,
        "circle": CircleModuleDrawer,
        "gapped": GappedSquareModuleDrawer,
    }[dot_style]()
    img = qr.make_image(image_factory=StyledPilImage, module_drawer=drawer).convert("RGB")
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            pixels[x, y] = fg if pixels[x, y][0] < 128 else bg
    size = max(100, min(size, 2000))
    img = img.resize((size, size), Image.LANCZOS)
    out = Path("qr_styled.png")
    img.save(out)
    return out
