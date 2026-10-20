# pdf, metadata, info, inspect

from pathlib import Path
import pymupdf


def pdf_info(pdf: Path) -> dict:
    """Show a PDF's metadata (title, author, dates, producer), page count and sizes, encryption, fonts, images, links
    and text/word counts.
    """
    with pymupdf.open(pdf) as doc:
        meta = {k: v for k, v in (doc.metadata or {}).items() if v}
        sizes = {}
        fonts = set()
        images = 0
        words = 0
        links = 0
        for page in doc:
            w, h = round(page.rect.width / 72 * 25.4), round(page.rect.height / 72 * 25.4)
            label = f"{w}x{h} mm"
            sizes[label] = sizes.get(label, 0) + 1
            fonts.update(f[3] for f in page.get_fonts())
            images += len(page.get_images())
            words += len(page.get_text("words"))
            links += len(page.get_links())
        return {
            "file": pdf.name,
            "file_size_bytes": pdf.stat().st_size,
            "pages": doc.page_count,
            "page_sizes": sizes,
            "metadata": meta or "none",
            "encrypted": doc.is_encrypted,
            "pdf_version": meta.get("format", "unknown"),
            "has_form_fields": bool(doc.is_form_pdf),
            "has_bookmarks": len(doc.get_toc()) > 0,
            "words": words,
            "images": images,
            "links": links,
            "fonts": sorted(fonts)[:40],
        }
