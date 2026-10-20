# network, cidr, subnet, ip range, split, summarize

from typing import Literal
import ipaddress


def cidr_tools(
    input: str = "192.168.0.0/22",
    action: Literal[
        "split_into_subnets", "expand_range_to_cidrs", "summarize_cidrs", "list_hosts", "check_overlap"
    ] = "split_into_subnets",
    new_prefix: int = 24,
) -> dict:
    """Subnet maths: split a block into smaller subnets, turn a start-end range into
    CIDRs, summarise several CIDRs into the fewest blocks, list a small subnet's
    hosts, or check whether two blocks overlap.
    """
    text = input.strip()
    try:
        if action == "split_into_subnets":
            net = ipaddress.ip_network(text, strict=False)
            if new_prefix <= net.prefixlen:
                return {"error": f"new_prefix must be larger than /{net.prefixlen}"}
            subnets = list(net.subnets(new_prefix=new_prefix))
            return {"network": str(net), "subnets": [str(s) for s in subnets[:1024]], "count": len(subnets)}
        if action == "expand_range_to_cidrs":
            start, end = [ipaddress.ip_address(p.strip()) for p in text.replace("to", "-").split("-")]
            return {"cidrs": [str(c) for c in ipaddress.summarize_address_range(start, end)]}
        if action == "summarize_cidrs":
            nets = [
                ipaddress.ip_network(p.strip(), strict=False)
                for p in text.replace(";", ",").replace("\n", ",").split(",")
                if p.strip()
            ]
            return {"summarized": [str(c) for c in ipaddress.collapse_addresses(nets)]}
        if action == "list_hosts":
            net = ipaddress.ip_network(text, strict=False)
            if net.num_addresses > 1024:
                return {"error": "Too many hosts to list (more than 1024); split the block first"}
            return {"network": str(net), "hosts": [str(h) for h in net.hosts()]}
        a, b = [ipaddress.ip_network(p.strip(), strict=False) for p in text.replace(";", ",").split(",")[:2]]
        return {
            "a": str(a),
            "b": str(b),
            "overlap": a.overlaps(b),
            "a_contains_b": b.subnet_of(a),
            "b_contains_a": a.subnet_of(b),
        }
    except ValueError as e:
        return {"error": str(e)}
