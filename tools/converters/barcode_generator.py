# barcode, ean, upc, code128, isbn, generator

from pathlib import Path
from typing import Literal
import barcode
from barcode.writer import ImageWriter, SVGWriter


def barcode_generator(
    data: str = "5901234123457",
    symbology: Literal["ean13", "ean8", "upca", "code128", "code39", "isbn13", "issn", "itf"] = "ean13",
    output: Literal["png", "svg"] = "png",
    show_text: Literal["yes", "no"] = "yes",
) -> dict:
    """Generate a barcode image (EAN-13, EAN-8, UPC-A, Code 128, Code 39, ISBN, ISSN,
    ITF). EAN/UPC check digits are added automatically when the last digit is left
    off.
    """
    text = data.strip()
    try:
        cls = barcode.get_barcode_class(symbology)
        writer = ImageWriter() if output == "png" else SVGWriter()
        code = cls(text, writer=writer)
        out = Path(f"barcode_{symbology}")
        saved = code.save(
            str(out), options={"write_text": show_text == "yes", "module_height": 12.0, "quiet_zone": 4.0}
        )
    except Exception as e:  # noqa: BLE001 - python-barcode raises several error types
        return {"error": f"Cannot encode '{data}' as {symbology}: {e}"}
    return {"file": Path(saved), "encoded": code.get_fullcode(), "symbology": symbology}
