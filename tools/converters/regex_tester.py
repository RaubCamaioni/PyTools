# regex, text, test, search

from typing import Literal
import re


def regex_tester(
    pattern: str,
    text: str,
    ignore_case: Literal["no", "yes"] = "no",
    replacement: str = "",
) -> dict:
    """Run a Python regular expression against text: lists every match with its position and groups, and shows the
    result of re.sub when a replacement is given.
    """
    flags = re.IGNORECASE if ignore_case == "yes" else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid pattern: {e}"}

    matches = []
    for m in regex.finditer(text):
        entry = {"match": m.group(0), "start": m.start(), "end": m.end()}
        if m.groups():
            entry["groups"] = list(m.groups())
        if m.groupdict():
            entry["named_groups"] = m.groupdict()
        matches.append(entry)
        if len(matches) >= 200:
            break

    result = {
        "pattern": pattern,
        "match_count": len(matches),
        "full_match": regex.fullmatch(text) is not None,
        "matches": matches,
    }
    if replacement:
        try:
            result["substituted"] = regex.sub(replacement, text)
        except re.error as e:
            result["substituted"] = f"Invalid replacement: {e}"
    return result
