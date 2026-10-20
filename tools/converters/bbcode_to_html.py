# bbcode, html, forum, markup, converter

from pathlib import Path
from typing import Literal
import html
import re

SIMPLE = {
    "b": "strong",
    "i": "em",
    "u": "u",
    "s": "s",
    "code": "code",
    "quote": "blockquote",
    "list": "ul",
    "center": "center",
    "sub": "sub",
    "sup": "sup",
}


def bbcode_to_html(text_file: Path, direction: Literal["bbcode_to_html", "html_to_bbcode"] = "bbcode_to_html") -> Path:
    """Convert forum BBCode ([b], [i], [url=], [img], [quote], [list], [color=],
    [size=]) to HTML, or simple HTML back to BBCode.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    if direction == "html_to_bbcode":
        out_text = text
        for tag, bb in (
            ("strong", "b"),
            ("b", "b"),
            ("em", "i"),
            ("i", "i"),
            ("u", "u"),
            ("s", "s"),
            ("code", "code"),
            ("blockquote", "quote"),
            ("ul", "list"),
            ("li", "*"),
        ):
            out_text = re.sub(rf"<{tag}[^>]*>", f"[{bb}]" if bb != "*" else "[*]", out_text, flags=re.I)
            out_text = re.sub(rf"</{tag}>", f"[/{bb}]" if bb != "*" else "", out_text, flags=re.I)
        out_text = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[url=\1]\2[/url]", out_text, flags=re.I | re.S)
        out_text = re.sub(r'<img\s+[^>]*src="([^"]+)"[^>]*/?>', r"[img]\1[/img]", out_text, flags=re.I)
        out_text = re.sub(r"<br\s*/?>", "\n", out_text, flags=re.I)
        out_text = re.sub(r"</?p[^>]*>", "\n", out_text, flags=re.I)
        out_text = html.unescape(re.sub(r"<[^>]+>", "", out_text))
        out = text_file.with_suffix(".bbcode.txt")
        out.write_text(out_text.strip() + "\n", encoding="utf-8")
        return out
    escaped = html.escape(text, quote=False)
    for bb, tag in SIMPLE.items():
        escaped = re.sub(rf"\[{bb}\]", f"<{tag}>", escaped, flags=re.I)
        escaped = re.sub(rf"\[/{bb}\]", f"</{tag}>", escaped, flags=re.I)
    escaped = re.sub(r"\[\*\]\s*(.*)", r"<li>\1</li>", escaped)
    escaped = re.sub(r"\[url=([^\]]+)\](.*?)\[/url\]", r'<a href="\1">\2</a>', escaped, flags=re.I | re.S)
    escaped = re.sub(r"\[url\](.*?)\[/url\]", r'<a href="\1">\1</a>', escaped, flags=re.I | re.S)
    escaped = re.sub(r"\[img\](.*?)\[/img\]", r'<img src="\1" alt="">', escaped, flags=re.I | re.S)
    escaped = re.sub(
        r"\[color=([#\w]+)\](.*?)\[/color\]", r'<span style="color:\1">\2</span>', escaped, flags=re.I | re.S
    )
    escaped = re.sub(
        r"\[size=(\d+)\](.*?)\[/size\]",
        lambda m: f'<span style="font-size:{min(int(m.group(1)), 72)}px">{m.group(2)}</span>',
        escaped,
        flags=re.I | re.S,
    )
    escaped = re.sub(r"\[quote=([^\]]+)\]", r"<blockquote><cite>\1</cite>", escaped, flags=re.I)
    escaped = escaped.replace("\n", "<br>\n")
    out = text_file.with_suffix(".html")
    out.write_text(escaped + "\n", encoding="utf-8")
    return out
