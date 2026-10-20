# random, pick, shuffle, groups, lottery, generator

from pathlib import Path
from typing import Literal
import random


def random_picker(
    items_file: Path,
    action: Literal["pick_one", "pick_several", "shuffle", "split_into_groups", "random_order_numbered"] = "pick_one",
    count: int = 3,
) -> dict:
    """Pick one or several random entries from a list (one per line), shuffle it, or
    split it into N random groups: raffles, team pickers and seating orders.
    """
    items = [line.strip() for line in items_file.read_text(encoding="utf-8-sig", errors="replace").splitlines()]
    items = [i for i in items if i]
    if not items:
        return {"error": "The list is empty"}
    count = max(1, count)

    if action == "pick_one":
        return {"picked": random.choice(items), "from": len(items)}
    if action == "pick_several":
        return {"picked": random.sample(items, min(count, len(items))), "from": len(items)}

    shuffled = items[:]
    random.shuffle(shuffled)
    if action == "shuffle":
        out = items_file.with_name(f"{items_file.stem}_shuffled.txt")
        out.write_text("\n".join(shuffled) + "\n", encoding="utf-8")
        return {"file": out, "items": len(shuffled)}
    if action == "random_order_numbered":
        return {"order": [f"{i}. {item}" for i, item in enumerate(shuffled, 1)]}

    groups = [shuffled[i::count] for i in range(min(count, len(shuffled)))]
    return {f"group_{i}": group for i, group in enumerate(groups, 1)}
