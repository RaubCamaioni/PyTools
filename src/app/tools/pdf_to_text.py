from contextlib import closing, ExitStack
from pathlib import Path
import pymupdf


def pdf_to_text(pdf_file: Path):
    text_file = pdf_file.with_suffix(".txt")

    with ExitStack() as stack:
        pdf = stack.enter_context(closing(pymupdf.open(pdf_file)))
        text = stack.enter_context(open(text_file, "w"))

        for page in pdf:
            text.write(page.get_text())

    return text_file
