# text, reverse, transform, words, sort, dedupe, rotate

from typing import Literal
import random


def text_transform(
    input: str,
    operation: Literal[
        "reverse_characters",
        "reverse_words",
        "sort_words",
        "sort_words_by_length",
        "shuffle_words",
        "remove_duplicate_words",
        "count_words",
        "upside_down",
        "strikethrough",
        "small_caps",
        "wide_text",
        "zalgo_light",
    ] = "reverse_characters",
) -> str:
    """Quick one-line text tricks: reverse characters or words, sort, shuffle or dedupe
    the words, count them, or restyle the text as upside-down, strikethrough, small
    caps, wide (vaporwave) or lightly glitched Unicode.
    """
    words = input.split()
    if operation == "reverse_characters":
        return input[::-1]
    if operation == "reverse_words":
        return " ".join(reversed(words))
    if operation == "sort_words":
        return " ".join(sorted(words, key=str.casefold))
    if operation == "sort_words_by_length":
        return " ".join(sorted(words, key=len))
    if operation == "shuffle_words":
        random.shuffle(words)
        return " ".join(words)
    if operation == "remove_duplicate_words":
        return " ".join(dict.fromkeys(words))
    if operation == "count_words":
        return f"{len(words)} words, {len(input)} characters, {len(input.replace(' ', ''))} without spaces"
    if operation == "upside_down":
        table = str.maketrans(
            "abcdefghijklmnopqrstuvwxyz0123456789.,?!'", "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz0ƖᄅƐㄣϛ9ㄥ86˙'¿¡,"
        )
        return input.lower().translate(table)[::-1]
    if operation == "strikethrough":
        return "".join(c + "̶" for c in input)
    if operation == "small_caps":
        table = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ")
        return input.lower().translate(table)
    if operation == "wide_text":
        return "".join(chr(ord(c) + 0xFEE0) if 33 <= ord(c) <= 126 else ("　" if c == " " else c) for c in input)
    marks = [chr(c) for c in range(0x0300, 0x036F)]
    return "".join(c + "".join(random.choice(marks) for _ in range(2)) if c.strip() else c for c in input)
