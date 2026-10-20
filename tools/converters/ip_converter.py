# network, ip, cidr, subnet, converter

import ipaddress


def ip_converter(input: str = "192.168.1.10/24") -> dict:
    """Convert an IPv4/IPv6 address to decimal, hex, binary and reverse-DNS form; a CIDR block (10.0.0.0/8) also gives
    netmask, broadcast, host range and count.
    """
    text = input.strip()
    try:
        if "/" in text:
            net = ipaddress.ip_network(text, strict=False)
            addr = ipaddress.ip_interface(text).ip
        else:
            try:
                addr = ipaddress.ip_address(int(text)) if text.isdigit() else ipaddress.ip_address(text)
            except ValueError:
                addr = ipaddress.ip_address(int(text, 16)) if text.lower().startswith("0x") else None
            if addr is None:
                raise ValueError
            net = None
    except ValueError:
        return {"error": f"'{input}' is not an IP address, integer, hex or CIDR block."}

    bits = 32 if addr.version == 4 else 128
    result = {
        "address": str(addr),
        "version": f"IPv{addr.version}",
        "integer": int(addr),
        "hex": f"0x{int(addr):0{bits // 4}x}",
        "binary": (
            ".".join(f"{int(o):08b}" for o in str(addr).split(".")) if addr.version == 4 else f"{int(addr):0128b}"
        ),
        "reverse_pointer": addr.reverse_pointer,
        "is_private": addr.is_private,
        "is_global": addr.is_global,
        "is_loopback": addr.is_loopback,
        "is_multicast": addr.is_multicast,
    }
    if addr.version == 6:
        result["exploded"] = addr.exploded
        result["compressed"] = addr.compressed
        if addr.ipv4_mapped:
            result["ipv4_mapped"] = str(addr.ipv4_mapped)
    else:
        result["ipv6_mapped"] = f"::ffff:{addr}"

    if net is not None:
        hosts = net.num_addresses - (2 if addr.version == 4 and net.prefixlen < 31 else 0)
        result["network"] = {
            "cidr": str(net),
            "netmask": str(net.netmask),
            "wildcard_mask": str(net.hostmask),
            "prefix_length": net.prefixlen,
            "network_address": str(net.network_address),
            "broadcast_address": str(net.broadcast_address),
            "first_host": str(net.network_address + (1 if hosts > 0 and net.prefixlen < 31 else 0)),
            "last_host": str(net.broadcast_address - (1 if hosts > 0 and net.prefixlen < 31 else 0)),
            "total_addresses": net.num_addresses,
            "usable_hosts": max(hosts, 0),
        }
    return result
