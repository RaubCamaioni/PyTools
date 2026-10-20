# audio, tags, id3, metadata, mp3, flac, cover

from pathlib import Path
from typing import Literal
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.mp3 import MP3

FIELDS = ("title", "artist", "album", "albumartist", "date", "genre", "tracknumber", "discnumber", "composer")


def audio_tags(
    audio: Path,
    action: Literal["read", "write", "strip_all"] = "read",
    title: str = "",
    artist: str = "",
    album: str = "",
    year: str = "",
    genre: str = "",
    track_number: str = "",
) -> dict:
    """Read, edit or strip the tags (ID3, Vorbis, MP4) of an MP3, FLAC, OGG, M4A or WAV
    file: title, artist, album, year, genre, track number, plus embedded cover art on
    read.
    """
    if action == "read":
        info = mutagen.File(str(audio), easy=True)
        if info is None:
            return {"error": "Unrecognised audio file"}
        tags = {k: info.get(k, [""])[0] for k in FIELDS if info.get(k)}
        result = {
            "format": type(info).__name__,
            "length_seconds": round(info.info.length, 1),
            "bitrate_kbps": getattr(info.info, "bitrate", 0) // 1000,
            "tags": tags,
        }
        cover = _cover(audio)
        if cover is not None:
            result["cover_art"] = cover
        return result

    out = audio.with_name(f"{audio.stem}_tagged{audio.suffix}")
    out.write_bytes(audio.read_bytes())
    if action == "strip_all":
        f = mutagen.File(str(out))
        if f is not None:
            f.delete()
            f.save()
        return {"file": out, "tags": {}}

    try:
        f = mutagen.File(str(out), easy=True)
        if f is None:
            return {"error": "Unrecognised audio file"}
        if f.tags is None:
            f.add_tags()
    except ID3NoHeaderError:
        f = MP3(str(out), ID3=EasyID3)
        f.add_tags()
    for key, value in (
        ("title", title),
        ("artist", artist),
        ("album", album),
        ("date", year),
        ("genre", genre),
        ("tracknumber", track_number),
    ):
        if value.strip():
            f[key] = value.strip()
    f.save()
    return {"file": out, "tags": {k: f.get(k, [""])[0] for k in FIELDS if f.get(k)}}


def _cover(audio: Path):
    try:
        id3 = ID3(str(audio))
    except Exception:  # noqa: BLE001 - not an ID3 file
        return None
    for frame in id3.values():
        if isinstance(frame, APIC):
            ext = "jpg" if "jpeg" in frame.mime else "png"
            out = audio.with_name(f"{audio.stem}_cover.{ext}")
            out.write_bytes(frame.data)
            return out
    return None
