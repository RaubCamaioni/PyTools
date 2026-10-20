# qr, code, image, scan, decode

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def qr_code_reader(image: Path) -> dict:
    """Read every QR code in an image (photo or screenshot) and return the decoded text."""
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()
    results = []
    ok, texts, points, _ = detector.detectAndDecodeMulti(frame)
    if ok:
        for text, quad in zip(texts, points):
            if text:
                x, y = quad.mean(axis=0)
                results.append({"text": text, "center": (int(x), int(y))})

    if not results:
        # second try: upscale small images and binarise
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if max(gray.shape) < 600:
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text, _, _ = detector.detectAndDecode(binary)
        if text:
            results.append({"text": text})

    return {"codes_found": len(results), "codes": results} if results else {"codes_found": 0, "message": "No QR code could be decoded. Try a sharper, better-lit image."}
