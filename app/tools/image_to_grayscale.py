from pathlib import Path
import cv2


def image_to_grayscale(file: Path) -> Path:
    image = cv2.imread(file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_path = f"{file.stem}_gray{file.suffix}"
    cv2.imwrite(gray_path, gray)
    return Path(gray_path)
