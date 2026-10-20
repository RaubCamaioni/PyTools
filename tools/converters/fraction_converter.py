# number, fraction, decimal, percent, converter

from fractions import Fraction
import math
import re


def fraction_converter(input: str = "0.375", max_denominator: int = 10000) -> dict:
    """Convert between fractions, mixed numbers, decimals, percentages and ratios: 3/8, 1 1/2, 0.375, 37.5%, 3:8 are all accepted."""
    text = input.strip().replace(" ", " ")
    try:
        if "%" in text:
            value = Fraction(text.replace("%", "").strip()) / 100
        elif ":" in text:
            a, b = text.split(":")
            value = Fraction(a.strip()) / Fraction(b.strip())
        elif m := re.fullmatch(r"(-?\d+)\s+(\d+)/(\d+)", text):
            whole, num, den = (int(x) for x in m.groups())
            value = Fraction(abs(whole) * den + num, den) * (-1 if whole < 0 else 1)
        else:
            value = Fraction(text)
    except (ValueError, ZeroDivisionError):
        return {"error": f"Could not understand '{input}'. Try 3/8, 1 1/2, 0.375, 37.5% or 3:8."}

    simplified = value.limit_denominator(max(1, max_denominator))
    whole = int(simplified)
    remainder = abs(simplified - whole)
    mixed = f"{whole} {remainder.numerator}/{remainder.denominator}" if whole and remainder else str(simplified)
    decimal = float(simplified)

    def repeating(fr: Fraction) -> str:
        n, d = abs(fr.numerator), fr.denominator
        integer, n = divmod(n, d)
        digits, seen = [], {}
        while n and n not in seen:
            seen[n] = len(digits)
            n *= 10
            digits.append(str(n // d))
            n %= d
        sign = "-" if fr < 0 else ""
        if not n:
            return f"{sign}{integer}." + "".join(digits) if digits else f"{sign}{integer}"
        start = seen[n]
        return f"{sign}{integer}." + "".join(digits[:start]) + "(" + "".join(digits[start:]) + ")"

    return {
        "fraction": str(simplified),
        "mixed_number": mixed,
        "decimal": decimal,
        "exact_decimal": repeating(simplified),
        "percent": f"{decimal * 100:g}%",
        "ratio": f"{simplified.numerator}:{simplified.denominator}",
        "reciprocal": str(1 / simplified) if simplified else "undefined",
        "approximation_used": simplified != value,
        "nearest_common_fractions": {
            f"1/{d}ths": str(value.limit_denominator(d)) for d in (2, 4, 8, 16, 32, 64) if value.limit_denominator(d) != simplified
        },
        "gcd_of_terms_before_simplifying": math.gcd(value.numerator, value.denominator),
    }
