# archive, zip, tar, 7z, gzip, compress, converter

from pathlib import Path
from typing import Literal
import gzip
import shutil
import tarfile
import tempfile
import zipfile
import py7zr


def safe_extract_dir(archive: Path, target: Path):
    suffixes = "".join(archive.suffixes).lower()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                dest = (target / member.filename).resolve()
                if not str(dest).startswith(str(target.resolve())):
                    raise ValueError("archive contains unsafe paths")
            zf.extractall(target)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                dest = (target / member.name).resolve()
                if not str(dest).startswith(str(target.resolve())) or member.issym() or member.islnk():
                    raise ValueError("archive contains unsafe paths or links")
            if hasattr(tarfile, "data_filter"):
                tf.extractall(target, filter="data")
            else:
                tf.extractall(target)
    elif py7zr.is_7zfile(archive):
        with py7zr.SevenZipFile(archive) as sz:
            sz.extractall(target)
    elif suffixes.endswith(".gz"):
        with gzip.open(archive, "rb") as src, open(target / archive.name[:-3], "wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        raise ValueError("Input must be a .zip, .tar, .tar.gz, .tgz, .7z or .gz file")


def archive_converter(
    archive: Path,
    output: Literal["zip", "tar_gz", "tar", "7z", "list_contents"] = "zip",
) -> dict:
    """Convert between ZIP, TAR, TAR.GZ and 7Z archives (or decompress a .gz file), or list what an archive contains
    without extracting.
    """
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        work = Path(tmp)
        safe_extract_dir(archive, work)
        files = sorted(p for p in work.rglob("*") if p.is_file())
        listing = [{"path": str(p.relative_to(work)).replace("\\", "/"), "bytes": p.stat().st_size} for p in files]

        if output == "list_contents":
            return {
                "archive": archive.name,
                "files": len(listing),
                "total_bytes": sum(f["bytes"] for f in listing),
                "contents": listing[:500],
            }

        stem = archive.name.split(".")[0] or "archive"
        if output == "zip":
            out = Path(f"{stem}.zip")
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in files:
                    zf.write(p, p.relative_to(work))
        elif output == "7z":
            out = Path(f"{stem}.7z")
            with py7zr.SevenZipFile(out, "w") as sz:
                sz.writeall(work, arcname="")
        else:
            out = Path(f"{stem}.tar.gz" if output == "tar_gz" else f"{stem}.tar")
            with tarfile.open(out, "w:gz" if output == "tar_gz" else "w") as tf:
                for p in files:
                    tf.add(p, arcname=str(p.relative_to(work)))
    return {
        "file": out,
        "files": len(listing),
        "input_bytes": archive.stat().st_size,
        "output_bytes": out.stat().st_size,
    }
