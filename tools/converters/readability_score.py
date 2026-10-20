# text, readability, flesch, grade level, writing

from pathlib import Path
import re


def readability_score(text_file: Path) -> dict:
    """Score how easy a text is to read: Flesch Reading Ease, Flesch-Kincaid grade,
    Gunning Fog, SMOG, Coleman-Liau and ARI, with the sentence and word statistics
    behind them.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not words or not sentences:
        return {"error": "Not enough text to score"}

    def syllables(word: str) -> int:
        w = word.lower().strip("'")
        count = len(re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and not w.endswith(("le", "ee")) and count > 1:
            count -= 1
        return max(1, count)

    syl = [syllables(w) for w in words]
    n_words, n_sent, n_syl = len(words), len(sentences), sum(syl)
    complex_words = sum(1 for s in syl if s >= 3)
    letters = sum(len(w) for w in words)
    wps, spw = n_words / n_sent, n_syl / n_words
    flesch = 206.835 - 1.015 * wps - 84.6 * spw
    fk = 0.39 * wps + 11.8 * spw - 15.59
    fog = 0.4 * (wps + 100 * complex_words / n_words)
    smog = 1.043 * (30 * complex_words / n_sent) ** 0.5 + 3.1291
    cli = 0.0588 * (letters / n_words * 100) - 0.296 * (n_sent / n_words * 100) - 15.8
    ari = 4.71 * letters / n_words + 0.5 * wps - 21.43
    bands = [
        (90, "very easy (5th grade)"),
        (80, "easy (6th grade)"),
        (70, "fairly easy (7th grade)"),
        (60, "plain English (8th-9th grade)"),
        (50, "fairly hard (10th-12th grade)"),
        (30, "hard (college)"),
        (0, "very hard (graduate)"),
    ]
    ease = next(label for limit, label in bands if flesch >= limit)
    return {
        "flesch_reading_ease": round(flesch, 1),
        "reading_ease_meaning": ease,
        "flesch_kincaid_grade": round(fk, 1),
        "gunning_fog": round(fog, 1),
        "smog": round(smog, 1),
        "coleman_liau": round(cli, 1),
        "automated_readability_index": round(ari, 1),
        "average_grade_level": round((fk + fog + smog + cli + ari) / 5, 1),
        "words": n_words,
        "sentences": n_sent,
        "words_per_sentence": round(wps, 1),
        "syllables_per_word": round(spw, 2),
        "complex_words_percent": round(complex_words / n_words * 100, 1),
    }
