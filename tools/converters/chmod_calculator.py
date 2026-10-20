# chmod, permissions, linux, unix, octal

import re


def chmod_calculator(permissions: str = "755") -> dict:
    """Convert Unix file permissions between octal (755), symbolic (rwxr-xr-x) and a
    readable table of owner/group/others, with the matching chmod command.
    """
    text = permissions.strip()
    if re.fullmatch(r"[0-7]{3,4}", text):
        octal = text[-3:]
        special = int(text[0]) if len(text) == 4 else 0
    elif re.fullmatch(r"[-dl]?[rwxsStT-]{9}", text):
        bits = text[-9:]
        octal, special = "", 0
        for i in range(3):
            chunk = bits[i * 3 : i * 3 + 3]
            value = (
                (4 if chunk[0] == "r" else 0) + (2 if chunk[1] == "w" else 0) + (1 if chunk[2].lower() in "xst" else 0)
            )
            if chunk[2] in "sS":
                special |= 4 if i == 0 else 2
            if chunk[2] in "tT":
                special |= 1
            octal += str(value)
    else:
        return {"error": f"'{permissions}' is neither octal like 755 nor symbolic like rwxr-xr-x"}

    names = ("owner", "group", "others")
    table, symbolic = {}, ""
    for who, digit in zip(names, octal):
        value = int(digit)
        r, w, x = value & 4, value & 2, value & 1
        table[who] = {"read": bool(r), "write": bool(w), "execute": bool(x), "octal": value}
        symbolic += ("r" if r else "-") + ("w" if w else "-") + ("x" if x else "-")
    if special & 4:
        symbolic = symbolic[:2] + ("s" if symbolic[2] == "x" else "S") + symbolic[3:]
    if special & 2:
        symbolic = symbolic[:5] + ("s" if symbolic[5] == "x" else "S") + symbolic[6:]
    if special & 1:
        symbolic = symbolic[:8] + ("t" if symbolic[8] == "x" else "T")
    full = f"{special}{octal}" if special else octal
    return {
        "octal": full,
        "symbolic": symbolic,
        "table": table,
        "special_bits": {"setuid": bool(special & 4), "setgid": bool(special & 2), "sticky": bool(special & 1)},
        "command": f"chmod {full} <file>",
        "symbolic_command": "chmod u={},g={},o={} <file>".format(
            symbolic[0:3].replace("-", ""), symbolic[3:6].replace("-", ""), symbolic[6:9].replace("-", "")
        ),
    }
