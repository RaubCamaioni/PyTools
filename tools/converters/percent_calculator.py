# percent, percentage, calculator, change, discount

from typing import Literal


def percent_calculator(
    calculation: Literal[
        "x_percent_of_y",
        "x_is_what_percent_of_y",
        "percent_change_from_x_to_y",
        "add_x_percent_to_y",
        "subtract_x_percent_from_y",
        "y_is_x_percent_of_what",
    ] = "x_percent_of_y",
    x: float = 15,
    y: float = 80,
) -> dict:
    """Everyday percentage sums: X% of Y, what percent X is of Y, the change from X to
    Y, adding or taking off X% (tax, discount, tip), or the whole when Y is X% of it.
    """
    try:
        if calculation == "x_percent_of_y":
            return {"answer": round(x / 100 * y, 4), "sentence": f"{x:g}% of {y:g} is {x / 100 * y:g}"}
        if calculation == "x_is_what_percent_of_y":
            return {"answer": round(x / y * 100, 4), "sentence": f"{x:g} is {x / y * 100:g}% of {y:g}"}
        if calculation == "percent_change_from_x_to_y":
            change = (y - x) / abs(x) * 100
            return {
                "answer": round(change, 4),
                "sentence": f"from {x:g} to {y:g} is a {abs(change):g}% {'increase' if change >= 0 else 'decrease'}",
            }
        if calculation == "add_x_percent_to_y":
            return {"answer": round(y * (1 + x / 100), 4), "sentence": f"{y:g} plus {x:g}% is {y * (1 + x / 100):g}"}
        if calculation == "subtract_x_percent_from_y":
            return {"answer": round(y * (1 - x / 100), 4), "sentence": f"{y:g} minus {x:g}% is {y * (1 - x / 100):g}"}
        return {"answer": round(y / (x / 100), 4), "sentence": f"{y:g} is {x:g}% of {y / (x / 100):g}"}
    except ZeroDivisionError:
        return {"error": "Division by zero; check the values"}
