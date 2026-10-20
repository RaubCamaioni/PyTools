# pdf, merge, combine, join

from pathlib import Path
import pymupdf


def pdf_merge(first_pdf: Path, second_pdf: Path, third_pdf: Path) -> Path:
    """Merge two or three PDFs into one, in order. Upload the same file twice if you
    only have two (duplicates are skipped).
    """
    doc = pymupdf.open()
    seen = set()
    for pdf in (first_pdf, second_pdf, third_pdf):
        key = (pdf.name, pdf.stat().st_size)
        if key in seen:
            continue
        seen.add(key)
        with pymupdf.open(pdf) as src:
            doc.insert_pdf(src)
    out = Path(f"{first_pdf.stem}_merged.pdf")
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return out
