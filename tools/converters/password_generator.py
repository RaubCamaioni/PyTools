# password, random, generator

from typing import Literal
import secrets
import string
import math


def password_generator(
    length: int = 16,
    count: int = 5,
    uppercase: Literal["yes", "no"] = "yes",
    digits: Literal["yes", "no"] = "yes",
    symbols: Literal["yes", "no"] = "yes",
    exclude_ambiguous: Literal["no", "yes"] = "no",
) -> dict:
    """Generate random passwords with a cryptographically secure generator and report
    their entropy.
    """
    length = max(4, min(length, 128))
    count = max(1, min(count, 50))
    pool = string.ascii_lowercase
    if uppercase == "yes":
        pool += string.ascii_uppercase
    if digits == "yes":
        pool += string.digits
    if symbols == "yes":
        pool += "!@#$%^&*()-_=+[]{};:,.<>?"
    if exclude_ambiguous == "yes":
        pool = "".join(c for c in pool if c not in "0O1lI|`'\"")
    passwords = ["".join(secrets.choice(pool) for _ in range(length)) for _ in range(count)]
    entropy = round(length * math.log2(len(pool)), 1)
    return {"passwords": passwords, "entropy_bits": entropy, "alphabet_size": len(pool)}
