# subtitle, srt, vtt, caption, converter

from pathlib import Path
from typing import Literal
import re

TIME = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)|(\d+):(\d+)[.,](\d+)")


def parse_time(text: str) -> float:
    m = TIME.search(text)
    if not m:
        raise ValueError(f"bad timestamp: {text}")
    if m.group(1) is not None:
        h, mi, s, ms = (int(x) for x in m.groups()[:4])
    else:
        h, mi, s, ms = 0, int(m.group(5)), int(m.group(6)), int(m.group(7))
    return h * 3600 + mi * 60 + s + ms / 1000


def fmt(seconds: float, sep: str) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)):03d}"


def parse_cues(text: str) -> list[tuple[float, float, str]]:
    cues = []
    blocks = re.split(r"\n\s*\n", text.strip().replace("\r\n", "\n"))
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        a, b = lines[idx].split("-->")
        body = "\n".join(lines[idx + 1 :])
        body = re.sub(r"<[^>]+>", "", body) if "{" not in body else body
        cues.append((parse_time(a), parse_time(b), body))
    return cues


def subtitle_converter(
    subtitle_file: Path,
    output: Literal["vtt", "srt", "plain_text", "csv"] = "vtt",
    shift_seconds: float = 0,
) -> Path:
    """Convert subtitles between SRT and WebVTT, strip them to plain text or CSV, and optionally shift all timings by a
    number of seconds (negative to move earlier).
    """
    text = subtitle_file.read_text(encoding="utf-8-sig", errors="replace")
    cues = parse_cues(text)
    if not cues:
        raise ValueError("No subtitle cues found (expected SRT or VTT with --> timings)")
    cues = [(a + shift_seconds, b + shift_seconds, body) for a, b, body in cues]

    if output == "srt":
        chunks = [f"{i}\n{fmt(a, ',')} --> {fmt(b, ',')}\n{body}\n" for i, (a, b, body) in enumerate(cues, 1)]
        content = "\n".join(chunks)
        ext = "srt"
    elif output == "vtt":
        chunks = [f"{fmt(a, '.')} --> {fmt(b, '.')}\n{body}\n" for a, b, body in cues]
        content = "WEBVTT\n\n" + "\n".join(chunks)
        ext = "vtt"
    elif output == "csv":
        import csv
        import io

        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["start", "end", "text"])
        for a, b, body in cues:
            w.writerow([fmt(a, "."), fmt(b, "."), body.replace("\n", " ")])
        content, ext = buf.getvalue(), "csv"
    else:
        content = "\n".join(body.replace("\n", " ") for _, _, body in cues) + "\n"
        ext = "txt"

    out = subtitle_file.with_suffix("." + ext)
    out.write_text(content, encoding="utf-8")
    return out
