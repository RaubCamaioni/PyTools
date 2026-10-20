# password, strength, security, check

from zxcvbn import zxcvbn


def password_strength(password: str) -> dict:
    """Score a password's strength (0 weak to 4 strong) the way zxcvbn does: guesses
    needed, estimated crack times at several attack speeds, and what makes it weak.
    """
    if not password:
        return {"error": "Enter a password"}
    result = zxcvbn(password[:200])
    times = result["crack_times_display"]
    return {
        "score_0_to_4": result["score"],
        "guesses": int(result["guesses"]),
        "guesses_log10": round(result["guesses_log10"], 1),
        "crack_time_online_throttled": times["online_throttling_100_per_hour"],
        "crack_time_online_unthrottled": times["online_no_throttling_10_per_second"],
        "crack_time_offline_slow_hash": times["offline_slow_hashing_1e4_per_second"],
        "crack_time_offline_fast_hash": times["offline_fast_hashing_1e10_per_second"],
        "warning": result["feedback"]["warning"] or "",
        "suggestions": result["feedback"]["suggestions"],
        "patterns_found": [f"{m['pattern']}: {m['token']}" for m in result["sequence"]],
    }
