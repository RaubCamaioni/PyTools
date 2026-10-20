# random, number, dice, coin, lottery, generator

from typing import Literal
import re
import secrets


def random_number_generator(
    mode: Literal[
        "numbers_in_range", "dice_notation", "coin_flips", "lottery_6_of_49", "unique_numbers_in_range"
    ] = "numbers_in_range",
    low: int = 1,
    high: int = 100,
    count: int = 5,
    dice: str = "2d6+3",
) -> dict:
    """Cryptographically random numbers: integers in a range (with or without repeats),
    dice rolls in RPG notation like 2d6+3, coin flips, or a lottery draw.
    """
    count = max(1, min(count, 1000))
    if mode == "coin_flips":
        flips = [secrets.choice(["heads", "tails"]) for _ in range(count)]
        return {"flips": flips, "heads": flips.count("heads"), "tails": flips.count("tails")}
    if mode == "dice_notation":
        m = re.fullmatch(r"\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*", dice.lower())
        if not m:
            return {"error": "Use notation like d20, 2d6 or 3d8+2"}
        n, sides = int(m.group(1) or 1), int(m.group(2))
        modifier = int(m.group(3).replace(" ", "")) if m.group(3) else 0
        n, sides = max(1, min(n, 100)), max(2, min(sides, 1000))
        rolls = [secrets.randbelow(sides) + 1 for _ in range(n)]
        return {
            "dice": f"{n}d{sides}{modifier:+d}" if modifier else f"{n}d{sides}",
            "rolls": rolls,
            "total": sum(rolls) + modifier,
        }
    if mode == "lottery_6_of_49":
        pool = list(range(1, 50))
        draw = sorted(pool.pop(secrets.randbelow(len(pool))) for _ in range(6))
        return {"numbers": draw, "bonus": pool.pop(secrets.randbelow(len(pool)))}
    lo, hi = min(low, high), max(low, high)
    if mode == "unique_numbers_in_range":
        span = hi - lo + 1
        if count > span:
            return {"error": f"Only {span} distinct numbers exist between {lo} and {hi}"}
        chosen, seen = [], set()
        while len(chosen) < count:
            n = lo + secrets.randbelow(span)
            if n not in seen:
                seen.add(n)
                chosen.append(n)
        return {"numbers": chosen}
    return {"numbers": [lo + secrets.randbelow(hi - lo + 1) for _ in range(count)]}
