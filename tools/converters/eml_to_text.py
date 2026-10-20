# email, eml, text, attachments, converter

from pathlib import Path
from typing import Literal
import email
import re
import zipfile
from email import policy


def eml_to_text(eml_file: Path, output: Literal["text", "html", "attachments_zip"] = "text") -> dict:
    """Read a saved email (.eml): headers and the message body as text or HTML, or pull
    out its attachments into a zip.
    """
    message = email.message_from_bytes(eml_file.read_bytes(), policy=policy.default)
    headers = {k: str(message.get(k, "")) for k in ("From", "To", "Cc", "Date", "Subject")}
    attachments = [part for part in message.iter_attachments()]

    if output == "attachments_zip":
        out = eml_file.with_name(f"{eml_file.stem}_attachments.zip")
        names = []
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, part in enumerate(attachments, 1):
                name = part.get_filename() or f"attachment_{i}"
                names.append(name)
                zf.writestr(name, part.get_payload(decode=True) or b"")
        return {"file": out, "attachments": names, "headers": headers}

    body = message.get_body(preferencelist=("html",) if output == "html" else ("plain", "html"))
    content = body.get_content() if body is not None else ""
    if output == "text" and body is not None and body.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", "", content)
    head = "\n".join(f"{k}: {v}" for k, v in headers.items() if v)
    out = eml_file.with_suffix(".html" if output == "html" else ".txt")
    if output == "html":
        out.write_text(f"<pre>{head}</pre>\n<hr>\n{content}", encoding="utf-8")
    else:
        out.write_text(head + "\n\n" + content.strip() + "\n", encoding="utf-8")
    return {"file": out, "headers": headers, "attachments": [p.get_filename() for p in attachments]}
