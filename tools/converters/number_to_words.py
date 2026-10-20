# number, words, text, converter

from typing import Literal
from num2words import num2words


def number_to_words(
    number: str = "1234.56",
    style: Literal[
        "cardinal", "ordinal", "ordinal_number", "year", "currency_usd", "currency_eur", "currency_gbp"
    ] = "cardinal",
    language: Literal["en", "es", "fr", "de", "it", "pt", "nl"] = "en",
) -> str:
    """Spell out a number in words (one thousand two hundred...), as an ordinal, a year
    or a currency amount, in several languages.
    """
    text = number.strip().replace(",", "").replace(" ", "")
    try:
        value = int(text) if text.lstrip("-").isdigit() else float(text)
    except ValueError:
        return f"'{number}' is not a number."

    if style.startswith("currency"):
        currency = style.split("_")[1].upper()
        return num2words(value, lang=language, to="currency", currency=currency)
    if style in ("ordinal", "ordinal_number", "year"):
        value = int(value)
        return num2words(value, lang=language, to="ordinal_num" if style == "ordinal_number" else style)
    return num2words(value, lang=language)
