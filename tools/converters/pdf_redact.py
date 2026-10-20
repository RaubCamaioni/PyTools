# pdf, redact, black out, remove, privacy

from pathlib import Path
from typing import Literal
import re
import pymupdf


def pdf_redact(
    pdf: Path,
    text_to_remove: str,
    mode: Literal["exact_text", "regex", "emails", "phone_numbers", "numbers"] = "exact_text",
    ignore_case: Literal["yes", "no"] = "yes",
) -> dict:
    """Permanently black out text in a PDF: an exact phrase, a regular expression, or
    every email address, phone number or number. The text is removed from the file,
    not just covered.
    """
    patterns = {
        "emails": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "phone_numbers": r"\+?\d[\d\s().-]{7,}\d",
        "numbers": r"\d[\d,.]*",
    }
    if mode == "exact_text":
        if not text_to_remove.strip():
            return {"error": "Enter the text to remove"}
        pattern = re.escape(text_to_remove.strip())
    else:
        pattern = patterns.get(mode, text_to_remove)
    flags = re.IGNORECASE if ignore_case == "yes" else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid pattern: {e}"}

    count = 0
    with pymupdf.open(pdf) as doc:
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(s["text"] for s in spans)
                    for m in regex.finditer(text):
                        start, end = m.span()
                        pos = 0
                        for s in spans:
                            s_start, s_end = pos, pos + len(s["text"])
                            pos = s_end
                            if s_end <= start or s_start >= end:
                                continue
                            rect = pymupdf.Rect(s["bbox"])
                            frac0 = max(0, start - s_start) / max(1, len(s["text"]))
                            frac1 = min(len(s["text"]), end - s_start) / max(1, len(s["text"]))
                            box = pymupdf.Rect(
                                rect.x0 + rect.width * frac0, rect.y0, rect.x0 + rect.width * frac1, rect.y1
                            )
                            page.add_redact_annot(box, fill=(0, 0, 0))
                        count += 1
            page.apply_redactions()
        out = pdf.with_name(f"{pdf.stem}_redacted.pdf")
        doc.save(out, garbage=4, deflate=True)
    return {"file": out, "matches_removed": count}
