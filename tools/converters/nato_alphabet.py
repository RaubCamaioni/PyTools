# text, nato, phonetic, alphabet, spelling, converter

from typing import Literal

NATO = {
    "A": "Alfa",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu",
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
    "-": "Dash",
    ".": "Stop",
    " ": "(space)",
}
REVERSE = {v.lower(): k for k, v in NATO.items()}


def nato_alphabet(input: str, mode: Literal["text_to_nato", "nato_to_text"]) -> str:
    """Spell text with the NATO phonetic alphabet (Alfa Bravo Charlie...) or turn
    spelled words back into text. Letters keep their case through capitalised vs
    lower-case code words.
    """
    if mode == "text_to_nato":
        words = []
        for ch in input:
            word = NATO.get(ch.upper())
            if word is None:
                words.append(ch)
            else:
                words.append(word if ch.isupper() or not ch.isalpha() else word.lower())
        return " ".join(words)

    out = []
    for word in input.split():
        key = REVERSE.get(word.lower())
        if key is None:
            out.append(word)
        elif key == " ":
            out.append(" ")
        else:
            out.append(key if word[0].isupper() or not key.isalpha() else key.lower())
    return "".join(out)
