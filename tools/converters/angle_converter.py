# unit, angle, degrees, radians, converter

from typing import Literal
import math
import re


def angle_converter(
    value: str = "45",
    unit: Literal[
        "degrees", "radians", "gradians", "turns", "arcminutes", "arcseconds", "degrees_minutes_seconds"
    ] = "degrees",
) -> dict:
    """Convert an angle between degrees, radians (accepts 'pi/4'), gradians, turns,
    arcminutes, arcseconds and degrees-minutes-seconds (45°30'15'').
    """
    text = value.strip().lower()
    try:
        if unit == "degrees_minutes_seconds":
            nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]
            if not nums:
                raise ValueError
            sign = -1 if text.startswith("-") else 1
            nums = [abs(n) for n in nums] + [0, 0]
            degrees = sign * (nums[0] + nums[1] / 60 + nums[2] / 3600)
        else:
            if "pi" in text or "π" in text:
                # forms such as pi, 2pi, 3*pi/2, pi/4, 0.5π
                m = re.fullmatch(r"(-?)\s*([\d.]*)\s*\*?\s*(?:pi|π)\s*(?:/\s*([\d.]+))?", text)
                if not m:
                    raise ValueError
                sign, coefficient, divisor = m.groups()
                number = math.pi * float(coefficient or 1) / float(divisor or 1)
                if sign:
                    number = -number
            else:
                number = float(text)
            factors = {
                "degrees": 1,
                "radians": 180 / math.pi,
                "gradians": 0.9,
                "turns": 360,
                "arcminutes": 1 / 60,
                "arcseconds": 1 / 3600,
            }
            degrees = number * factors[unit]
    except (ValueError, SyntaxError, ZeroDivisionError):
        return {"error": f"Could not parse '{value}' as {unit}."}

    normalized = degrees % 360
    d = int(abs(degrees))
    m = int((abs(degrees) - d) * 60)
    s = (abs(degrees) - d - m / 60) * 3600
    radians = math.radians(degrees)
    return {
        "degrees": float(f"{degrees:.8g}"),
        "radians": float(f"{radians:.8g}"),
        "radians_in_pi": f"{radians / math.pi:.6g}π",
        "gradians": float(f"{degrees / 0.9:.8g}"),
        "turns": float(f"{degrees / 360:.8g}"),
        "arcminutes": float(f"{degrees * 60:.8g}"),
        "arcseconds": float(f"{degrees * 3600:.8g}"),
        "degrees_minutes_seconds": f"{'-' if degrees < 0 else ''}{d}° {m}' {s:.2f}\"",
        "normalized_0_360": float(f"{normalized:.8g}"),
        "sin": round(math.sin(radians), 6),
        "cos": round(math.cos(radians), 6),
        "tan": round(math.tan(radians), 6) if abs(math.cos(radians)) > 1e-12 else "undefined",
    }
