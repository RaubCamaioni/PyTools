# cooking, baking, cups, grams, ounces, recipe, converter

from typing import Literal

# grams per US cup for common ingredients
GRAMS_PER_CUP = {
    "water": 237,
    "milk": 244,
    "all_purpose_flour": 125,
    "bread_flour": 127,
    "whole_wheat_flour": 120,
    "granulated_sugar": 200,
    "brown_sugar_packed": 220,
    "powdered_sugar": 120,
    "butter": 227,
    "vegetable_oil": 218,
    "honey": 340,
    "cocoa_powder": 85,
    "rolled_oats": 90,
    "rice_uncooked": 185,
    "salt": 288,
    "chocolate_chips": 170,
    "peanut_butter": 258,
    "yogurt": 245,
}
CUP_ML = 236.588
UNITS_ML = {
    "cup": CUP_ML,
    "tablespoon": 14.787,
    "teaspoon": 4.929,
    "fluid_ounce": 29.574,
    "milliliter": 1.0,
    "liter": 1000.0,
    "pint": 473.176,
    "quart": 946.353,
}


def cooking_converter(
    amount: float = 1,
    unit: Literal[
        "cup",
        "tablespoon",
        "teaspoon",
        "fluid_ounce",
        "milliliter",
        "liter",
        "pint",
        "quart",
        "gram",
        "ounce_weight",
        "pound",
    ] = "cup",
    ingredient: Literal[
        "water",
        "milk",
        "all_purpose_flour",
        "bread_flour",
        "whole_wheat_flour",
        "granulated_sugar",
        "brown_sugar_packed",
        "powdered_sugar",
        "butter",
        "vegetable_oil",
        "honey",
        "cocoa_powder",
        "rolled_oats",
        "rice_uncooked",
        "salt",
        "chocolate_chips",
        "peanut_butter",
        "yogurt",
    ] = "all_purpose_flour",
) -> dict:
    """Convert recipe amounts between cups, spoons, millilitres and grams for a specific
    ingredient (a cup of flour is not a cup of sugar), plus oven temperatures in a
    handy table.
    """
    density = GRAMS_PER_CUP[ingredient] / CUP_ML  # grams per ml
    if unit == "gram":
        grams = amount
    elif unit == "ounce_weight":
        grams = amount * 28.3495
    elif unit == "pound":
        grams = amount * 453.592
    else:
        grams = amount * UNITS_ML[unit] * density
    ml = grams / density
    result = {
        "ingredient": ingredient,
        "grams": round(grams, 1),
        "ounces_weight": round(grams / 28.3495, 2),
        "cups": round(ml / CUP_ML, 3),
        "tablespoons": round(ml / UNITS_ML["tablespoon"], 1),
        "teaspoons": round(ml / UNITS_ML["teaspoon"], 1),
        "milliliters": round(ml, 1),
        "fluid_ounces": round(ml / UNITS_ML["fluid_ounce"], 2),
        "oven_temperatures": {
            "gas mark 4 / moderate": "180 °C / 350 °F",
            "gas mark 6 / hot": "200 °C / 400 °F",
            "gas mark 2 / cool": "150 °C / 300 °F",
            "fan oven": "subtract about 20 °C",
        },
    }
    return result
