# text, morse, encoding, converter

from typing import Literal

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.",
    "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.",
    "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-",
    "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
    "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--", "/": "-..-.",
    "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
REVERSE = {v: k for k, v in MORSE.items()}


def morse_code(input: str, mode: Literal["text_to_morse", "morse_to_text"]) -> str:
    """Translate text to International Morse code (letters separated by spaces, words by ' / ') and back."""
    if mode == "text_to_morse":
        words = input.upper().split()
        return " / ".join(" ".join(MORSE.get(c, "?") for c in word) for word in words)

    words = input.replace("|", "/").split("/")
    decoded = []
    for word in words:
        decoded.append("".join(REVERSE.get(sym, "?") for sym in word.split()))
    return " ".join(decoded).strip()
