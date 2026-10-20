# pdf, reorder, pages, reverse, duplicate, organize

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_reorder(
    pdf: Path,
    action: Literal[
        "custom_order", "reverse", "odd_then_even", "interleave_from_two_scans", "duplicate_each_page"
    ] = "custom_order",
    order: str = "3,1,2",
) -> Path:
    """Rearrange a PDF's pages: an explicit order such as 3,1,2,5-8 (pages may repeat),
    reverse the document, odd pages then even, fix a double-sided scan (front pages
    then back pages reversed), or duplicate every page.
    """
    with pymupdf.open(pdf) as doc:
        n = doc.page_count
        if action == "reverse":
            sequence = list(range(n - 1, -1, -1))
        elif action == "odd_then_even":
            sequence = list(range(0, n, 2)) + list(range(1, n, 2))
        elif action == "interleave_from_two_scans":
            half = (n + 1) // 2
            fronts, backs = list(range(half)), list(range(n - 1, half - 1, -1))
            sequence = [
                p for pair in zip(fronts, backs + [None] * (len(fronts) - len(backs))) for p in pair if p is not None
            ]
        elif action == "duplicate_each_page":
            sequence = [i for i in range(n) for _ in range(2)]
        else:
            sequence = []
            for part in order.replace(" ", "").split(","):
                a, _, b = part.partition("-")
                if a:
                    sequence.extend(range(int(a) - 1, int(b or a)))
            sequence = [i for i in sequence if 0 <= i < n]
            if not sequence:
                raise ValueError(f"No valid pages in '{order}' (the document has {n} pages)")
        doc.select(sequence)
        out = pdf.with_name(f"{pdf.stem}_{action}.pdf")
        doc.save(out, garbage=3, deflate=True)
    return out
