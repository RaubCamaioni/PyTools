# phone, number, format, e164, country, parse

import phonenumbers
from phonenumbers import carrier, geocoder, timezone as phone_tz


def phone_number_parser(number: str = "+44 20 7946 0958", default_region: str = "US") -> dict:
    """Parse and format a phone number: validity, country, type (mobile, landline...),
    E.164, international and national formats. Numbers without a country code use the
    default region.
    """
    try:
        parsed = phonenumbers.parse(number.strip(), default_region.strip().upper() or None)
    except phonenumbers.NumberParseException as e:
        return {"valid": False, "reason": str(e)}
    kinds = {v: k for k, v in vars(phonenumbers.PhoneNumberType).items() if isinstance(v, int)}
    return {
        "valid": phonenumbers.is_valid_number(parsed),
        "possible": phonenumbers.is_possible_number(parsed),
        "country_code": f"+{parsed.country_code}",
        "region": phonenumbers.region_code_for_number(parsed),
        "location": geocoder.description_for_number(parsed, "en"),
        "carrier": carrier.name_for_number(parsed, "en") or "",
        "time_zones": list(phone_tz.time_zones_for_number(parsed)),
        "type": kinds.get(phonenumbers.number_type(parsed), "unknown").lower(),
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "rfc3966": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966),
    }
