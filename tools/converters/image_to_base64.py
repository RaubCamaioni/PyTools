# image, base64, data, uri, converter

from pathlib import Path
from typing import Literal
import base64
import mimetypes


def image_to_base64(file: Path, output: Literal["data_uri", "raw_base64", "html_img_tag", "css_background"] = "data_uri") -> str:
    """Encode an image (or any file) as Base64, as a data: URI, or wrapped in an HTML <img> tag or CSS background rule."""
    data = file.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    uri = f"data:{mime};base64,{encoded}"
    if output == "raw_base64":
        return encoded
    if output == "html_img_tag":
        return f'<img src="{uri}" alt="{file.stem}">'
    if output == "css_background":
        return f"background-image: url('{uri}');"
    return uri
