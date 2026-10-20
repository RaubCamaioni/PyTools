# network, mac, address, format, generate

from typing import Literal
import re
import secrets


def mac_address_formatter(
    mac: str = "00:1A:2B:3C:4D:5E",
    action: Literal["format", "generate_random"] = "format",
    style: Literal["colon_lower", "colon_upper", "hyphen_upper", "dot_cisco", "plain"] = "colon_lower",
) -> dict:
    """Normalise a MAC address into the colon, hyphen, Cisco-dot or plain style, decode
    its flags (unicast/multicast, globally or locally administered), or generate a
    random locally-administered MAC.
    """
    if action == "generate_random":
        raw = bytearray(secrets.token_bytes(6))
        raw[0] = (raw[0] | 0x02) & 0xFE
        digits = raw.hex()
    else:
        digits = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
        if len(digits) != 12:
            return {"error": f"'{mac}' does not contain 12 hex digits"}
    pairs = [digits[i : i + 2] for i in range(0, 12, 2)]
    first = int(pairs[0], 16)
    formats = {
        "colon_lower": ":".join(pairs),
        "colon_upper": ":".join(pairs).upper(),
        "hyphen_upper": "-".join(pairs).upper(),
        "dot_cisco": ".".join(digits[i : i + 4] for i in range(0, 12, 4)),
        "plain": digits.upper(),
    }
    return {
        "formatted": formats[style],
        "all_formats": formats,
        "oui_vendor_prefix": "-".join(pairs[:3]).upper(),
        "multicast": bool(first & 1),
        "locally_administered": bool(first & 2),
        "eui64_interface_id": ":".join(
            [f"{first ^ 2:02x}" + pairs[1], pairs[2] + "ff", "fe" + pairs[3], pairs[4] + pairs[5]]
        ),
    }
