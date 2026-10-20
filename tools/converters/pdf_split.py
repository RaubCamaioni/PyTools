# pdf, split, extract, pages, remove

from pathlib import Path
from typing import Literal
import pymupdf
import zipfile


def parse_pages(spec: str, count: int) -> list[int]:
    pages: list[int] = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else count
        else:
            start = end = int(part)
        for p in range(start, end + 1):
            if 1 <= p <= count and (p - 1) not in pages:
                pages.append(p - 1)
    return pages


def pdf_split(
    pdf: Path,
    action: Literal["extract_pages", "remove_pages", "split_every_page", "split_in_two"] = "extract_pages",
    pages: str = "1-3",
) -> Path:
    """Extract or remove pages from a PDF (pages like 1-3,5,8-), split every page into its own file (zipped), or cut the document in two at the given page."""
    with pymupdf.open(pdf) as doc:
        count = doc.page_count

        if action == "split_every_page":
            out = Path(f"{pdf.stem}_pages.zip")
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for i in range(count):
                    single = pymupdf.open()
                    single.insert_pdf(doc, from_page=i, to_page=i)
                    zf.writestr(f"{pdf.stem}_page_{i + 1:03d}.pdf", single.tobytes(garbage=3, deflate=True))
                    single.close()
            return out

        if action == "split_in_two":
            cut = max(1, min(int(pages.split(",")[0].split("-")[0] or 1), count - 1))
            out = Path(f"{pdf.stem}_split.zip")
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for label, (a, b) in (("part1", (0, cut - 1)), ("part2", (cut, count - 1))):
                    part = pymupdf.open()
                    part.insert_pdf(doc, from_page=a, to_page=b)
                    zf.writestr(f"{pdf.stem}_{label}.pdf", part.tobytes(garbage=3, deflate=True))
                    part.close()
            return out

        selected = parse_pages(pages, count)
        if action == "remove_pages":
            selected = [i for i in range(count) if i not in selected]
        if not selected:
            raise ValueError(f"No pages selected (document has {count} pages)")
        doc.select(selected)
        out = Path(f"{pdf.stem}_{action}.pdf")
        doc.save(out, garbage=3, deflate=True)
    return out
