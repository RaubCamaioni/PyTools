# number, roman, converter

VALUES = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    out = ""
    for value, symbol in VALUES:
        while n >= value:
            out += symbol
            n -= value
    return out


def roman_numerals(input: str) -> str:
    """Convert an integer (1-3999) to Roman numerals, or Roman numerals back to an integer. Direction is detected
    automatically.
    """
    text = input.strip().upper()
    if text.isdigit():
        n = int(text)
        if not 1 <= n <= 3999:
            return "Enter a number between 1 and 3999."
        return to_roman(n)

    if not text or any(c not in "MDCLXVI" for c in text):
        return "Enter a whole number or Roman numerals (I V X L C D M)."
    singles = {s: v for v, s in VALUES if len(s) == 1}
    total = 0
    for i, c in enumerate(text):
        v = singles[c]
        if i + 1 < len(text) and singles[text[i + 1]] > v:
            total -= v
        else:
            total += v
    # a round trip rejects malformed numerals such as IIII or VX
    if not 1 <= total <= 3999 or to_roman(total) != text:
        return f"'{text}' is not a well-formed Roman numeral (closest value: {total})."
    return str(total)
