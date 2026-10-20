# text, count, words, statistics

from pathlib import Path
from collections import Counter
import re


def word_counter(text_file: Path, top_words: int = 10) -> dict:
    """Count characters, words, sentences, lines and paragraphs in a text file, with reading time and the most common
    words.
    """
    text = text_file.read_text(encoding="utf-8", errors="replace")
    words = re.findall(r"[A-Za-z0-9'-]+", text)
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    common = Counter(w.lower() for w in words if len(w) > 2).most_common(max(0, top_words))
    return {
        "characters": len(text),
        "characters_without_spaces": len(re.sub(r"\s", "", text)),
        "words": len(words),
        "unique_words": len({w.lower() for w in words}),
        "sentences": len(sentences),
        "lines": len(text.splitlines()),
        "paragraphs": len(paragraphs),
        "average_word_length": round(sum(map(len, words)) / len(words), 2) if words else 0,
        "reading_time_minutes": round(len(words) / 200, 1),
        "speaking_time_minutes": round(len(words) / 130, 1),
        "most_common_words": common,
    }
