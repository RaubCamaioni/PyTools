# font, ttf, otf, woff, woff2, webfont, converter

from pathlib import Path
from typing import Literal
from fontTools.ttLib import TTFont


def font_converter(font: Path, output: Literal["woff2", "woff", "ttf", "otf", "info_only"] = "woff2") -> dict:
    """Convert a font between TTF, OTF, WOFF and WOFF2 (web fonts), and report its
    family, style, glyph count and licence text.
    """
    try:
        f = TTFont(str(font))
    except Exception as e:  # noqa: BLE001
        return {"error": f"Not a font file fontTools can read: {e}"}
    names = {}
    for record in f["name"].names:
        try:
            names.setdefault(record.nameID, record.toUnicode())
        except UnicodeDecodeError:
            continue
    info = {
        "family": names.get(1, ""),
        "style": names.get(2, ""),
        "full_name": names.get(4, ""),
        "version": names.get(5, ""),
        "glyphs": len(f.getGlyphOrder()),
        "format": "CFF (OpenType)" if "CFF " in f else "TrueType",
        "units_per_em": f["head"].unitsPerEm,
        "licence": (names.get(13, "") or "")[:300],
    }
    if output == "info_only":
        return info
    if output == "otf" and "CFF " not in f:
        info["note"] = (
            "TrueType outlines cannot become CFF without re-drawing them; saved as .otf container with TrueType glyphs"
        )
    f.flavor = output if output in ("woff", "woff2") else None
    out = font.with_suffix("." + output)
    f.save(str(out))
    info["file"] = out
    info["bytes"] = out.stat().st_size
    return info
