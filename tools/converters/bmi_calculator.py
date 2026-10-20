# bmi, health, weight, height, calculator

from typing import Literal


def bmi_calculator(
    weight: float = 70,
    height: float = 175,
    units: Literal["metric_kg_cm", "imperial_lb_in"] = "metric_kg_cm",
) -> dict:
    """Body mass index from weight and height (kg and cm, or pounds and inches), with
    the WHO category and the weight range that would count as a healthy BMI for that
    height.
    """
    if units == "imperial_lb_in":
        kg, m = weight * 0.453592, height * 0.0254
    else:
        kg, m = weight, height / 100
    if kg <= 0 or m <= 0:
        return {"error": "Weight and height must be positive"}
    bmi = kg / (m * m)
    categories = [
        (18.5, "underweight"),
        (25, "healthy weight"),
        (30, "overweight"),
        (35, "obese (class I)"),
        (40, "obese (class II)"),
    ]
    category = next((name for limit, name in categories if bmi < limit), "obese (class III)")
    low, high = 18.5 * m * m, 24.9 * m * m
    to_imperial = lambda k: round(k / 0.453592, 1)  # noqa: E731
    return {
        "bmi": round(bmi, 1),
        "category": category,
        "healthy_weight_range": (
            f"{low:.1f} to {high:.1f} kg"
            if units == "metric_kg_cm"
            else f"{to_imperial(low)} to {to_imperial(high)} lb"
        ),
        "note": "BMI is a population screening number; it does not account for muscle, age or build",
    }
