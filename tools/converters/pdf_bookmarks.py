# pdf, bookmarks, outline, toc, chapters

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_bookmarks(
    pdf: Path,
    action: Literal["export", "import_from_text", "generate_from_headings", "remove"] = "export",
    bookmarks_text: str = "",
) -> dict:
    """Export a PDF's bookmarks (outline) as indented text, add bookmarks from text
    lines like `1 Introduction` or `  2 Methods` (page number, indent for nesting),
    guess them from large headings, or remove them all.
    """
    with pymupdf.open(pdf) as doc:
        if action == "export":
            toc = doc.get_toc()
            out = pdf.with_name(f"{pdf.stem}_bookmarks.txt")
            out.write_text(
                "".join("  " * (lvl - 1) + f"{page} {title}\n" for lvl, title, page in toc) or "(no bookmarks)\n",
                encoding="utf-8",
            )
            return {"file": out, "bookmarks": len(toc)}
        if action == "remove":
            doc.set_toc([])
        elif action == "import_from_text":
            toc = []
            for line in bookmarks_text.replace("\\n", "\n").splitlines():
                stripped = line.lstrip(" ")
                if not stripped:
                    continue
                level = (len(line) - len(stripped)) // 2 + 1
                page, _, title = stripped.partition(" ")
                if page.isdigit():
                    toc.append(
                        [max(1, min(level, 6)), title.strip() or f"Page {page}", max(1, min(int(page), doc.page_count))]
                    )
            doc.set_toc(toc)
        else:
            sizes = []
            for page in doc:
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if span["text"].strip():
                                sizes.append(span["size"])
            if not sizes:
                return {"error": "No text found to build bookmarks from"}
            body = sorted(sizes)[len(sizes) // 2]
            toc = []
            for number, page in enumerate(doc, 1):
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        text = "".join(s["text"] for s in line["spans"]).strip()
                        size = max((s["size"] for s in line["spans"]), default=0)
                        if text and size >= body * 1.3 and len(text) < 120:
                            toc.append([1 if size >= body * 1.6 else 2, text, number])
            if toc and toc[0][0] == 2:
                toc[0][0] = 1
            doc.set_toc(toc[:500])
        out = pdf.with_name(f"{pdf.stem}_{action}.pdf")
        doc.save(out, garbage=3, deflate=True)
        return {"file": out, "bookmarks": len(doc.get_toc())}
