# text, url, slug, converter

from typing import Literal
import re
import unicodedata


def slugify(input: str, separator: Literal["dash", "underscore"], lowercase: Literal["yes", "no"]) -> str:
    """Turn any text into a URL-safe slug: accents stripped, punctuation removed, words
    joined by - or _.
    """
    sep = "-" if separator == "dash" else "_"
    text = unicodedata.normalize("NFKD", input).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"['’`]", "", text)
    if lowercase == "yes":
        text = text.lower()
    text = re.sub(r"[^A-Za-z0-9]+", sep, text)
    return text.strip(sep)
