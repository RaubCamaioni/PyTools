# number, scientific, notation, engineering, converter

from decimal import Decimal, InvalidOperation
import re

SI = {
    -24: "y",
    -21: "z",
    -18: "a",
    -15: "f",
    -12: "p",
    -9: "n",
    -6: "µ",
    -3: "m",
    0: "",
    3: "k",
    6: "M",
    9: "G",
    12: "T",
    15: "P",
    18: "E",
    21: "Z",
    24: "Y",
}


def scientific_notation(input: str = "6.02214076e23", significant_digits: int = 4) -> dict:
    """Convert a number between plain decimal, scientific (1.23e5), engineering (123e3) notation and SI prefixes (123
    k). Accepts any of those as input.
    """
    text = (
        input.strip().replace(",", "").replace("×10^", "e").replace("x10^", "e").replace("*10^", "e").replace(" ", "")
    )
    text = re.sub(r"[Ee]\+?", "e", text)
    try:
        value = Decimal(text)
    except InvalidOperation:
        return {"error": f"Could not parse '{input}'. Try 123456, 1.23e5 or 1.23x10^5."}

    sig = max(1, min(significant_digits, 30))
    if value == 0:
        return {"decimal": "0", "scientific": "0e0", "engineering": "0e0", "si_prefix": "0", "exponent": 0}

    exponent = value.adjusted()
    mantissa = value.scaleb(-exponent)
    eng_exp = exponent - (exponent % 3)
    eng_mantissa = value.scaleb(-eng_exp)

    def fmt(d: Decimal) -> str:
        q = Decimal(1).scaleb(d.adjusted() - sig + 1)
        s = format(d.quantize(q), "f")
        return s.rstrip("0").rstrip(".") if "." in s else s

    si_prefix = SI.get(eng_exp)
    si = f"{fmt(eng_mantissa)} {si_prefix}" if si_prefix is not None else "out of SI range"
    plain = format(value, "f")
    return {
        "decimal": plain if len(plain) <= 60 else "too long to display",
        "scientific": f"{fmt(mantissa)}e{exponent}",
        "scientific_x10": f"{fmt(mantissa)} × 10^{exponent}",
        "engineering": f"{fmt(eng_mantissa)}e{eng_exp}",
        "si_prefix": si,
        "exponent": exponent,
        "order_of_magnitude": f"10^{exponent}",
        "significant_digits_shown": sig,
    }
