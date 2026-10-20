# pdf, image, extract, pictures

from pathlib import Path
import pymupdf
import zipfile


def pdf_extract_images(pdf: Path, min_size_px: int = 64) -> dict:
    """Pull every embedded picture out of a PDF (original resolution) into a zip. Tiny images such as icons and bullets
    are skipped by the size threshold.
    """
    out = Path(f"{pdf.stem}_images.zip")
    count = 0
    skipped = 0
    with pymupdf.open(pdf) as doc, zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
        seen = set()
        for page_index, page in enumerate(doc, 1):
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.width < min_size_px or pix.height < min_size_px:
                        skipped += 1
                        continue
                    if pix.n - pix.alpha >= 4:  # CMYK
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    ext = "png" if pix.alpha else "jpg"
                    data = pix.tobytes(ext, jpg_quality=92)
                    count += 1
                    zf.writestr(f"page{page_index:03d}_image{count:03d}.{ext}", data)
                except Exception:  # noqa: BLE001 - skip images mupdf cannot decode
                    skipped += 1
    return {"file": out, "images_extracted": count, "images_skipped": skipped}
