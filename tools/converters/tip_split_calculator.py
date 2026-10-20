# tip, bill, split, restaurant, calculator


def tip_split_calculator(
    bill: float = 86.40, tip_percent: float = 18, people: int = 4, round_up_per_person: float = 0
) -> dict:
    """Work out the tip, the total and each person's share of a bill, optionally
    rounding each share up to a convenient amount.
    """
    people = max(1, people)
    tip = bill * max(0.0, tip_percent) / 100
    total = bill + tip
    share = total / people
    if round_up_per_person > 0:
        step = round_up_per_person
        share = -(-share // step) * step
    return {
        "bill": round(bill, 2),
        "tip": round(tip, 2),
        "total": round(total, 2),
        "per_person": round(share, 2),
        "tip_per_person": round(tip / people, 2),
        "total_collected_if_rounded": round(share * people, 2),
        "other_tips": {f"{p}%": round(bill * p / 100, 2) for p in (10, 12, 15, 18, 20, 25)},
    }
