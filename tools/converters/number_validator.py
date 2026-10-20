# validate, iban, credit card, isbn, ean, vat, checksum

from typing import Literal
from stdnum import ean, iban, isbn, issn, luhn
from stdnum.eu import vat


def number_validator(
    number: str = "GB82 WEST 1234 5698 7654 32",
    kind: Literal["iban", "credit_card", "isbn", "ean_upc_barcode", "eu_vat", "issn"] = "iban",
) -> dict:
    """Check an IBAN, credit card number (Luhn), ISBN-10/13, EAN/UPC barcode, EU VAT
    number or ISSN: valid or not, why, and the normalised form. Nothing is looked up
    online.
    """
    text = number.strip()
    try:
        if kind == "iban":
            clean = iban.validate(text)
            return {
                "valid": True,
                "normalised": iban.format(clean),
                "country": clean[:2],
                "check_digits": clean[2:4],
                "bban": clean[4:],
            }
        if kind == "credit_card":
            digits = "".join(c for c in text if c.isdigit())
            luhn.validate(digits)
            brands = {
                "4": "Visa",
                "5": "Mastercard",
                "34": "American Express",
                "37": "American Express",
                "6": "Discover",
                "35": "JCB",
            }
            brand = next(
                (b for p, b in sorted(brands.items(), key=lambda x: -len(x[0])) if digits.startswith(p)), "unknown"
            )
            return {
                "valid": len(digits) in range(12, 20),
                "luhn_check": True,
                "brand_guess": brand,
                "length": len(digits),
                "masked": "*" * (len(digits) - 4) + digits[-4:],
            }
        if kind == "isbn":
            clean = isbn.validate(text)
            return {
                "valid": True,
                "normalised": isbn.format(clean),
                "isbn13": isbn.to_isbn13(clean),
                "isbn10": isbn.to_isbn10(clean) if len(clean) == 10 or clean.startswith("978") else None,
            }
        if kind == "ean_upc_barcode":
            clean = ean.validate(text)
            return {
                "valid": True,
                "normalised": clean,
                "type": {8: "EAN-8", 12: "UPC-A", 13: "EAN-13", 14: "GTIN-14"}.get(len(clean), "GTIN"),
            }
        if kind == "eu_vat":
            clean = vat.validate(text)
            return {"valid": True, "normalised": clean, "country": clean[:2]}
        clean = issn.validate(text)
        return {"valid": True, "normalised": issn.format(clean)}
    except Exception as e:  # noqa: BLE001 - stdnum raises a family of validation errors
        return {"valid": False, "reason": str(e) or type(e).__name__}
