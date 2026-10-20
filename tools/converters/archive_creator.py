# zip, archive, compress, password, gzip, bzip2, xz

from pathlib import Path
from typing import Literal
import bz2
import gzip
import lzma
import shutil
import tarfile
import zipfile
import pyzipper


def archive_creator(
    first_file: Path,
    second_file: Path,
    third_file: Path,
    format: Literal["zip", "zip_password_aes", "tar_gz", "gzip_each", "bzip2_each", "xz_each"] = "zip",
    password: str = "",
) -> dict:
    """Bundle up to three files into a zip (optionally AES-256 password protected), a
    tar.gz, or compress each file on its own with gzip, bzip2 or xz. Upload the same
    file twice if you have fewer than three.
    """
    files = []
    seen = set()
    for f in (first_file, second_file, third_file):
        key = (f.name, f.stat().st_size)
        if key not in seen:
            seen.add(key)
            files.append(f)
    before = sum(f.stat().st_size for f in files)

    if format in ("gzip_each", "bzip2_each", "xz_each"):
        opener, ext = {
            "gzip_each": (gzip.open, ".gz"),
            "bzip2_each": (bz2.open, ".bz2"),
            "xz_each": (lzma.open, ".xz"),
        }[format]
        out = Path("compressed.zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as zf:
            for f in files:
                packed = f.with_name(f.name + ext)
                with open(f, "rb") as src, opener(packed, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                zf.write(packed, packed.name)
        return {
            "file": out,
            "files": [f.name + ext for f in files],
            "before_bytes": before,
            "after_bytes": out.stat().st_size,
        }

    if format == "tar_gz":
        out = Path("archive.tar.gz")
        with tarfile.open(out, "w:gz") as tf:
            for f in files:
                tf.add(f, arcname=f.name)
    elif format == "zip_password_aes":
        if not password:
            return {"error": "A password is required for an encrypted zip"}
        out = Path("archive_encrypted.zip")
        with pyzipper.AESZipFile(out, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode("utf-8"))
            for f in files:
                zf.write(f, f.name)
    else:
        out = Path("archive.zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, f.name)
    return {"file": out, "files": [f.name for f in files], "before_bytes": before, "after_bytes": out.stat().st_size}
