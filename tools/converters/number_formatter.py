# number, format, currency, thousands, rounding, converter

from typing import Literal
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def number_formatter(
    number: str = "1234567.891",
    decimals: int = 2,
    style: Literal[
        "thousands_comma",
        "thousands_dot",
        "thousands_space",
        "plain",
        "currency_usd",
        "currency_eur",
        "currency_gbp",
        "percent",
        "accounting",
    ] = "thousands_comma",
) -> dict:
    """Format a number with thousands separators (1,234,567.89 or 1.234.567,89 or 1 234
    567,89), as a currency, a percentage or in accounting style with brackets for
    negatives.
    """
    text = number.strip().replace(" ", "")
    if text.count(",") and text.count(".") == 0 and len(text.split(",")[-1]) != 3:
        text = text.replace(",", ".")  # 1234,5 written the European way
    text = text.replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation:
        return {"error": f"'{number}' is not a number"}
    decimals = max(0, min(decimals, 10))
    rounded = value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    base = f"{abs(rounded):,.{decimals}f}"
    negative = rounded < 0
    if style == "thousands_dot":
        base = base.replace(",", "X").replace(".", ",").replace("X", ".")
    elif style == "thousands_space":
        base = base.replace(",", " ")
    elif style == "plain":
        base = f"{abs(rounded):.{decimals}f}"
    sign = "-" if negative else ""
    if style == "currency_usd":
        formatted = f"{sign}${base}"
    elif style == "currency_eur":
        formatted = f"{sign}{base.replace(',', 'X').replace('.', ',').replace('X', '.')} €"
    elif style == "currency_gbp":
        formatted = f"{sign}£{base}"
    elif style == "percent":
        formatted = f"{sign}{base}%"
    elif style == "accounting":
        formatted = f"({base})" if negative else base
    else:
        formatted = sign + base
    return {
        "formatted": formatted,
        "rounded": str(rounded),
        "scientific": f"{value:.{decimals}E}",
        "words_scale": _scale(abs(value)),
    }


def _scale(value: Decimal) -> str:
    for limit, word in (
        (Decimal(10**12), "trillion"),
        (Decimal(10**9), "billion"),
        (Decimal(10**6), "million"),
        (Decimal(10**3), "thousand"),
    ):
        if value >= limit:
            return f"{(value / limit):.2f} {word}"
    return str(value)
