# vcard, contact, qr, code, business card, generator

from pathlib import Path
from typing import Literal
import qrcode


def vcard_qr_code(
    full_name: str,
    phone: str = "",
    email: str = "",
    organisation: str = "",
    job_title: str = "",
    website: str = "",
    output: Literal["qr_png", "vcf_file", "both"] = "both",
) -> dict:
    """Build a contact card (vCard 3.0) and the QR code that adds it to a phone's
    contacts when scanned: name, phone, email, organisation, title and website.
    """
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{full_name.strip()}"]
    parts = full_name.strip().split()
    last = parts[-1] if len(parts) > 1 else ""
    first = " ".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else "")
    lines.append(f"N:{last};{first};;;")
    if phone.strip():
        lines.append(f"TEL;TYPE=CELL:{phone.strip()}")
    if email.strip():
        lines.append(f"EMAIL:{email.strip()}")
    if organisation.strip():
        lines.append(f"ORG:{organisation.strip()}")
    if job_title.strip():
        lines.append(f"TITLE:{job_title.strip()}")
    if website.strip():
        lines.append(f"URL:{website.strip()}")
    lines.append("END:VCARD")
    vcard = "\r\n".join(lines) + "\r\n"
    result = {"vcard": vcard}
    safe = "".join(c if c.isalnum() else "_" for c in full_name.strip()) or "contact"
    if output in ("vcf_file", "both"):
        vcf = Path(f"{safe}.vcf")
        vcf.write_text(vcard, encoding="utf-8")
        result["vcf_file"] = vcf
    if output in ("qr_png", "both"):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2, box_size=8)
        qr.add_data(vcard)
        qr.make(fit=True)
        png = Path(f"{safe}_qr.png")
        qr.make_image(fill_color="black", back_color="white").save(png)
        result["qr_code"] = png
    return result
