# pdf, n-up, pages per sheet, booklet, print

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_n_up(
    pdf: Path,
    layout: Literal["2_per_sheet", "4_per_sheet", "6_per_sheet", "9_per_sheet", "booklet"] = "2_per_sheet",
    sheet: Literal["a4", "letter"] = "a4",
) -> Path:
    """Put several pages on each sheet (2, 4, 6 or 9 up) or impose a booklet whose
    sheets fold in half into a stapled book.
    """
    width, height = (595, 842) if sheet == "a4" else (612, 792)
    with pymupdf.open(pdf) as src:
        out_doc = pymupdf.open()
        n = src.page_count
        if layout == "booklet":
            total = (n + 3) // 4 * 4
            order = []
            left, right = total - 1, 0
            while right < left:
                order += [(left, right), (right + 1, left - 1)]
                left, right = left - 2, right + 2
            for a, b in order:
                page = out_doc.new_page(width=height, height=width)
                for i, (x0, x1) in ((a, (0, height / 2)), (b, (height / 2, height))):
                    if i < n:
                        page.show_pdf_page(pymupdf.Rect(x0 + 10, 10, x1 - 10, width - 10), src, i)
        else:
            per = int(layout.split("_")[0])
            cols, rows = {2: (1, 2), 4: (2, 2), 6: (2, 3), 9: (3, 3)}[per]
            landscape = per == 2
            w, h = (height, width) if landscape else (width, height)
            if landscape:
                cols, rows = 2, 1
            cell_w, cell_h = w / cols, h / rows
            for start in range(0, n, per):
                page = out_doc.new_page(width=w, height=h)
                for k in range(per):
                    i = start + k
                    if i >= n:
                        break
                    r, c = divmod(k, cols)
                    box = pymupdf.Rect(c * cell_w + 8, r * cell_h + 8, (c + 1) * cell_w - 8, (r + 1) * cell_h - 8)
                    page.show_pdf_page(box, src, i)
        out = pdf.with_name(f"{pdf.stem}_{layout}.pdf")
        out_doc.save(out, garbage=3, deflate=True)
        out_doc.close()
    return out
