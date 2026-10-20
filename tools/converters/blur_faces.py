# image, face, blur, pixelate, privacy, anonymize

from pathlib import Path
from typing import Literal
import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def blur_faces(
    image: Path,
    style: Literal["blur", "pixelate", "black_box"] = "blur",
    strength: int = 50,
    sensitivity: Literal["normal", "high"] = "normal",
) -> dict:
    """Find faces in a photo and blur, pixelate or black them out. Uses OpenCV's frontal and profile face detectors (no upload leaves the sandbox). Returns the image and how many faces were found."""
    with Image.open(image) as src:
        rgb = ImageOps.exif_transpose(src).convert("RGB")
    frame = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    h, w = gray.shape
    min_size = max(20, int(min(h, w) * 0.04))
    neighbors = 3 if sensitivity == "high" else 5
    scale = 1.05 if sensitivity == "high" else 1.1

    boxes = []
    for name in ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml", "haarcascade_profileface.xml"):
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        found = cascade.detectMultiScale(gray, scaleFactor=scale, minNeighbors=neighbors, minSize=(min_size, min_size))
        boxes.extend([tuple(int(v) for v in b) for b in found])
        if name == "haarcascade_profileface.xml":
            flipped = cascade.detectMultiScale(cv2.flip(gray, 1), scaleFactor=scale, minNeighbors=neighbors, minSize=(min_size, min_size))
            boxes.extend([(w - int(x) - int(bw), int(y), int(bw), int(bh)) for x, y, bw, bh in flipped])

    merged = []
    for box in boxes:
        x, y, bw, bh = box
        for i, (mx, my, mw, mh) in enumerate(merged):
            ix = max(0, min(x + bw, mx + mw) - max(x, mx))
            iy = max(0, min(y + bh, my + mh) - max(y, my))
            if ix * iy > 0.3 * min(bw * bh, mw * mh):
                nx, ny = min(x, mx), min(y, my)
                merged[i] = (nx, ny, max(x + bw, mx + mw) - nx, max(y + bh, my + mh) - ny)
                break
        else:
            merged.append(box)

    strength = max(1, min(strength, 100))
    for x, y, bw, bh in merged:
        pad = int(bw * 0.15)
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + bw + pad), min(h, y + bh + pad)
        region = frame[y0:y1, x0:x1]
        if style == "black_box":
            frame[y0:y1, x0:x1] = 0
        elif style == "pixelate":
            blocks = max(2, int((x1 - x0) / (2 + strength / 6)))
            small = cv2.resize(region, (max(1, blocks), max(1, int(blocks * (y1 - y0) / max(1, x1 - x0)))), interpolation=cv2.INTER_LINEAR)
            frame[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        else:
            k = int((x1 - x0) * strength / 100) | 1
            frame[y0:y1, x0:x1] = cv2.GaussianBlur(region, (max(3, k), max(3, k)), 0)

    out = image.with_name(f"{image.stem}_faces_{style}.jpg")
    cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {"file": out, "faces_found": len(merged), "note": "" if merged else "No faces detected; try sensitivity=high or a larger, front-facing photo."}
