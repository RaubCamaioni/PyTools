# text, lists, compare, union, intersection, difference

from pathlib import Path
from typing import Literal


def list_operations(
    list_a: Path,
    list_b: Path,
    operation: Literal[
        "in_both", "in_a_only", "in_b_only", "in_either", "in_exactly_one", "a_then_b_deduplicated"
    ] = "in_both",
    ignore_case: Literal["no", "yes"] = "no",
) -> dict:
    """Compare two lists (one item per line): items in both, only in A, only in B, in
    either, in exactly one, or the two lists merged without duplicates. Order follows
    the first appearance.
    """

    def items(path: Path) -> list[str]:
        lines = [line.strip() for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines()]
        return [line for line in lines if line]

    a, b = items(list_a), items(list_b)
    key = (lambda s: s.lower()) if ignore_case == "yes" else (lambda s: s)
    set_a, set_b = {key(x) for x in a}, {key(x) for x in b}

    if operation == "in_both":
        result = [x for x in a if key(x) in set_b]
    elif operation == "in_a_only":
        result = [x for x in a if key(x) not in set_b]
    elif operation == "in_b_only":
        result = [x for x in b if key(x) not in set_a]
    elif operation == "in_either" or operation == "a_then_b_deduplicated":
        result = a + [x for x in b if key(x) not in set_a]
    else:
        result = [x for x in a if key(x) not in set_b] + [x for x in b if key(x) not in set_a]

    seen, unique = set(), []
    for x in result:
        if key(x) not in seen:
            seen.add(key(x))
            unique.append(x)
    out = Path(f"{operation}.txt")
    out.write_text("\n".join(unique) + "\n", encoding="utf-8")
    return {"file": out, "items_in_a": len(a), "items_in_b": len(b), "result_items": len(unique)}
