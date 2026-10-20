# pdf, word, docx, document, converter

from pathlib import Path
from typing import Literal
import logging
from pdf2docx import Converter


def pdf_to_word(pdf: Path, pages: str = "all", layout: Literal["keep_layout", "text_only"] = "keep_layout") -> Path:
    """Convert a PDF to an editable Word .docx, keeping text, tables, images and layout where possible. Scanned PDFs
    (images of text) come out as images; run OCR first for those.
    """
    logging.getLogger("pdf2docx").setLevel(logging.ERROR)
    out = pdf.with_suffix(".docx")

    start, end = 0, None
    if pages.strip().lower() != "all":
        part = pages.replace(" ", "").split(",")[0]
        a, _, b = part.partition("-")
        start = max(0, int(a or 1) - 1)
        end = int(b) if b else (start + 1 if not part.endswith("-") else None)

    converter = Converter(str(pdf))
    try:
        if layout == "text_only":
            # fall back to plain paragraphs: no floating images, no multi-column detection
            converter.convert(
                str(out),
                start=start,
                end=end,
                multi_processing=False,
                ignore_page_error=True,
                extract_stream_table=False,
                parse_lattice_table=False,
                parse_stream_table=False,
            )
        else:
            converter.convert(str(out), start=start, end=end, multi_processing=False, ignore_page_error=True)
    finally:
        converter.close()
    return out
