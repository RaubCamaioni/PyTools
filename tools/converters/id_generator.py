# id, ulid, nanoid, ksuid, snowflake, generator

from typing import Literal
import secrets
import time

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
NANO = "_-0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def id_generator(
    kind: Literal["ulid", "nanoid", "snowflake", "short_hex_token", "numeric_pin", "readable_code"] = "ulid",
    count: int = 5,
    length: int = 21,
) -> dict:
    """Generate identifiers other than UUIDs: sortable ULIDs, URL-safe NanoIDs,
    Twitter-style snowflakes, hex tokens, numeric PINs or human-readable codes like
    `K7PX-3RMA`.
    """
    count = max(1, min(count, 200))
    ids = []
    for i in range(count):
        if kind == "ulid":
            ms = int(time.time() * 1000)
            value = (ms << 80) | int.from_bytes(secrets.token_bytes(10), "big")
            ids.append("".join(CROCKFORD[(value >> (5 * (25 - j))) & 31] for j in range(26)))
        elif kind == "nanoid":
            ids.append("".join(secrets.choice(NANO) for _ in range(max(4, min(length, 64)))))
        elif kind == "snowflake":
            ms = int(time.time() * 1000) - 1288834974657
            ids.append(str((ms << 22) | (1 << 12) | (i & 0xFFF)))
        elif kind == "short_hex_token":
            ids.append(secrets.token_hex(max(2, min(length, 64)) // 2))
        elif kind == "numeric_pin":
            ids.append("".join(secrets.choice("0123456789") for _ in range(max(4, min(length, 12)))))
        else:
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            ids.append("-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2)))
    return {"kind": kind, "ids": ids}
