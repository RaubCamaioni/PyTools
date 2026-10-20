# shoe, size, clothing, us, uk, eu, converter

from typing import Literal


def shoe_size_converter(
    size: float = 9,
    system: Literal["us_men", "us_women", "uk", "eu", "cm", "inches"] = "us_men",
) -> dict:
    """Convert shoe sizes between US men's, US women's, UK, EU and foot length in
    cm/inches (standard adult sizing; brands vary by up to half a size).
    """
    if system == "us_men":
        cm = (size + 24) * 2.54 / 3
    elif system == "us_women":
        cm = (size + 22.5) * 2.54 / 3
    elif system == "uk":
        cm = (size + 25) * 2.54 / 3
    elif system == "eu":
        cm = size * 2 / 3
    elif system == "inches":
        cm = size * 2.54
    else:
        cm = size
    us_men = cm * 3 / 2.54 - 24
    return {
        "foot_length_cm": round(cm, 1),
        "foot_length_inches": round(cm / 2.54, 2),
        "us_men": round(us_men * 2) / 2,
        "us_women": round((us_men + 1.5) * 2) / 2,
        "uk": round((us_men - 1) * 2) / 2,
        "eu": round(cm * 1.5 * 2) / 2,
        "note": "EU sizes are Paris points (2/3 cm); US women's run 1.5 larger than men's",
    }
