# pdf, password, protect, unlock, encrypt

from pathlib import Path
from typing import Literal
import pymupdf


def pdf_password(
    pdf: Path,
    action: Literal["protect", "unlock"] = "protect",
    password: str = "",
) -> Path:
    """Protect a PDF with a password (AES-256, opening and editing) or remove the password from a PDF you know the password for."""
    if action == "protect":
        if not password:
            raise ValueError("A password is required to protect the file")
        with pymupdf.open(pdf) as doc:
            out = Path(f"{pdf.stem}_protected.pdf")
            doc.save(out, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password, permissions=pymupdf.PDF_PERM_ACCESSIBILITY | pymupdf.PDF_PERM_PRINT, garbage=3, deflate=True)
        return out

    with pymupdf.open(pdf) as doc:
        if doc.is_encrypted and not doc.authenticate(password):
            raise ValueError("Wrong password")
        out = Path(f"{pdf.stem}_unlocked.pdf")
        doc.save(out, encryption=pymupdf.PDF_ENCRYPT_NONE, garbage=3, deflate=True)
    return out
