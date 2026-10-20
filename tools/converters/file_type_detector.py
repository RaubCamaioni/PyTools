# file, type, detect, magic, extension, identify

from pathlib import Path
import zipfile

SIGNATURES = [
    (b"%PDF", "PDF document", ".pdf"),
    (b"\x89PNG\r\n\x1a\n", "PNG image", ".png"),
    (b"\xff\xd8\xff", "JPEG image", ".jpg"),
    (b"GIF87a", "GIF image", ".gif"),
    (b"GIF89a", "GIF image", ".gif"),
    (b"BM", "BMP image", ".bmp"),
    (b"II*\x00", "TIFF image", ".tif"),
    (b"MM\x00*", "TIFF image", ".tif"),
    (b"\x00\x00\x01\x00", "ICO icon", ".ico"),
    (b"Rar!\x1a\x07", "RAR archive", ".rar"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive", ".7z"),
    (b"\x1f\x8b", "gzip compressed", ".gz"),
    (b"BZh", "bzip2 compressed", ".bz2"),
    (b"\xfd7zXZ\x00", "xz compressed", ".xz"),
    (b"ID3", "MP3 audio (ID3)", ".mp3"),
    (b"\xff\xfb", "MP3 audio", ".mp3"),
    (b"\xff\xf3", "MP3 audio", ".mp3"),
    (b"fLaC", "FLAC audio", ".flac"),
    (b"OggS", "Ogg container (Vorbis/Opus)", ".ogg"),
    (b"\x1aE\xdf\xa3", "Matroska/WebM video", ".mkv"),
    (b"FLV", "Flash video", ".flv"),
    (b"MZ", "Windows executable", ".exe"),
    (b"\x7fELF", "Linux executable (ELF)", ""),
    (b"\xca\xfe\xba\xbe", "Java class / Mach-O fat binary", ""),
    (b"SQLite format 3\x00", "SQLite database", ".sqlite"),
    (b"{\\rtf", "Rich Text Format", ".rtf"),
    (b"\xd0\xcf\x11\xe0", "Legacy Office (doc/xls/ppt) or MSI", ".doc"),
    (b"wOFF", "WOFF web font", ".woff"),
    (b"wOF2", "WOFF2 web font", ".woff2"),
    (b"\x00\x01\x00\x00", "TrueType font", ".ttf"),
    (b"OTTO", "OpenType font", ".otf"),
    (b"<?xml", "XML document", ".xml"),
    (b"<svg", "SVG image", ".svg"),
    (b"<!DOCTYPE html", "HTML document", ".html"),
    (b"<html", "HTML document", ".html"),
    (b"\xef\xbb\xbf", "UTF-8 text with BOM", ".txt"),
    (b"-----BEGIN", "PEM certificate or key", ".pem"),
    (b"\x00asm", "WebAssembly", ".wasm"),
    (b"%!PS", "PostScript", ".ps"),
    (b"\x1f\x9d", "compress (.Z)", ".z"),
    (b"\x04\x22\x4d\x18", "LZ4 compressed", ".lz4"),
    (b"\x28\xb5\x2f\xfd", "Zstandard compressed", ".zst"),
]


def file_type_detector(file: Path) -> dict:
    """Identify what a file really is from its contents (magic bytes), not its name:
    images, documents, archives, audio/video, fonts, executables, text encodings.
    Flags mismatched extensions.
    """
    head = file.read_bytes()[:64]
    kind, ext = None, ""
    if head[:4] == b"RIFF" and len(head) >= 12:
        kind, ext = {
            b"WEBP": ("WebP image", ".webp"),
            b"WAVE": ("WAV audio", ".wav"),
            b"AVI ": ("AVI video", ".avi"),
        }.get(head[8:12], ("RIFF container", ""))
    elif head[4:8] == b"ftyp":
        brand = head[8:12]
        kind, ext = (
            ("HEIC/HEIF image", ".heic") if brand[:3] in (b"hei", b"mif", b"msf") else ("MP4/MOV/M4A container", ".mp4")
        )
    elif head[:4] == b"PK\x03\x04":
        kind, ext = "ZIP archive", ".zip"
        try:
            with zipfile.ZipFile(file) as zf:
                names = set(zf.namelist())
                if "word/document.xml" in names:
                    kind, ext = "Word document (docx)", ".docx"
                elif "xl/workbook.xml" in names:
                    kind, ext = "Excel workbook (xlsx)", ".xlsx"
                elif "ppt/presentation.xml" in names:
                    kind, ext = "PowerPoint (pptx)", ".pptx"
                elif "META-INF/container.xml" in names:
                    kind, ext = "EPUB ebook", ".epub"
                elif "mimetype" in names and zf.read("mimetype").startswith(b"application/vnd.oasis"):
                    kind, ext = "OpenDocument file", ".odt"
                elif "AndroidManifest.xml" in names:
                    kind, ext = "Android package (apk)", ".apk"
                elif any(n.endswith(".class") for n in names) or "META-INF/MANIFEST.MF" in names:
                    kind, ext = "Java archive (jar)", ".jar"
        except zipfile.BadZipFile:
            pass
    else:
        for sig, name, extension in SIGNATURES:
            if head.startswith(sig):
                kind, ext = name, extension
                break
    if kind is None:
        sample = file.read_bytes()[:4096]
        if sample and all(b in b"\t\n\r\x0b\x0c" or 32 <= b < 127 or b >= 128 for b in sample):
            try:
                sample.decode("utf-8")
                kind, ext = "plain text (UTF-8)", ".txt"
            except UnicodeDecodeError:
                kind, ext = "text (8-bit encoding)", ".txt"
        else:
            kind, ext = "unknown binary data", ""
    if kind == "XML document" and b"<svg" in file.read_bytes()[:4096]:
        kind, ext = "SVG image", ".svg"
    claimed = file.suffix.lower()
    aliases = {
        ".jpeg": ".jpg",
        ".tiff": ".tif",
        ".dng": ".tif",
        ".htm": ".html",
        ".m4a": ".mp4",
        ".mov": ".mp4",
        ".webm": ".mkv",
    }
    aliases.update({".ods": ".odt", ".odp": ".odt", ".xls": ".doc", ".ppt": ".doc", ".msi": ".doc", ".tgz": ".gz"})
    return {
        "detected": kind,
        "typical_extension": ext or "(none)",
        "file_extension": claimed or "(none)",
        "extension_matches": ext == "" or claimed == ext or aliases.get(claimed) == ext,
        "size_bytes": file.stat().st_size,
        "first_bytes_hex": head[:16].hex(" "),
    }
