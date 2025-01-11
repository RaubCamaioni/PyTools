# image

from pathlib import Path
import cv2


def image_to_grayscale(image_file: Path) -> Path:
    image = cv2.imread(image_file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_path = f"{image_file.stem}_gray{image_file.suffix}"
    cv2.imwrite(gray_path, gray)
    return Path(gray_path)
