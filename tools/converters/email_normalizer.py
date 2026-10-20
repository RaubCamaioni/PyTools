# email, validate, normalize, gmail, dots, plus

import re

LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@" + LABEL + r"(?:\." + LABEL + r")+$")
DISPOSABLE = {
    "mailinator.com",
    "guerrillamail.com",
    "10minutemail.com",
    "tempmail.com",
    "yopmail.com",
    "trashmail.com",
    "sharklasers.com",
    "getnada.com",
    "dispostable.com",
}


def email_normalizer(email: str = "John.Doe+newsletter@Gmail.com") -> dict:
    """Check an email address's syntax and normalise it: lower-case the domain, and for
    Gmail strip the dots and the +tag so aliases of the same inbox compare equal.
    Flags common disposable-mail domains. Nothing is sent or looked up online.
    """
    text = email.strip()
    if not PATTERN.match(text):
        return {"valid_syntax": False, "input": text}
    local, domain = text.rsplit("@", 1)
    domain = domain.lower()
    canonical_local = local
    notes = []
    if domain in ("gmail.com", "googlemail.com"):
        canonical_local = local.split("+")[0].replace(".", "").lower()
        domain = "gmail.com"
        notes.append("Gmail ignores dots and anything after +")
    elif domain in ("outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "protonmail.com", "proton.me"):
        canonical_local = local.split("+")[0].lower()
        notes.append("provider ignores +tags")
    else:
        canonical_local = local.split("+")[0]
    return {
        "valid_syntax": True,
        "normalised": f"{local.lower()}@{domain}",
        "canonical_inbox": f"{canonical_local}@{domain}",
        "local_part": local,
        "domain": domain,
        "has_plus_tag": "+" in local,
        "disposable_domain": domain in DISPOSABLE,
        "notes": notes,
    }
