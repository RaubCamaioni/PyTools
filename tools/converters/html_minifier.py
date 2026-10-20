# html, minify, beautify, format, compress

from pathlib import Path
from typing import Literal
from html.parser import HTMLParser
import re

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
INLINE = {"a", "b", "i", "em", "strong", "span", "code", "small", "sub", "sup", "u", "s", "abbr", "label", "br", "img"}
KEEP = {"pre", "textarea", "script", "style"}
BLOCK_NAMES = "html|head|body|title|meta|link|style|script|div|p|ul|ol|li|table|thead|tbody|tfoot|tr|td|th|h[1-6]|br|hr"
BLOCK_NAMES += "|section|article|header|footer|nav|main|aside|form|figure|blockquote|dl|dt|dd|option|select"
BLOCK_TAG = rf"</?(?:{BLOCK_NAMES})[^>]*>"


class Pretty(HTMLParser):
    def __init__(self, indent: int):
        super().__init__(convert_charrefs=False)
        self.out, self.depth, self.indent, self.keep = [], 0, " " * indent, 0

    def line(self, text):
        self.out.append(self.indent * self.depth + text if not self.keep else text)

    def handle_starttag(self, tag, attrs):
        attr_text = "".join(f' {k}="{v}"' if v is not None else f" {k}" for k, v in attrs)
        self.line(f"<{tag}{attr_text}>")
        if tag in KEEP:
            self.keep += 1
        if tag not in VOID:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.depth -= 1

    def handle_endtag(self, tag):
        if tag not in VOID:
            self.depth = max(0, self.depth - 1)
        if tag in KEEP:
            self.keep = max(0, self.keep - 1)
        self.line(f"</{tag}>")

    def handle_data(self, data):
        if self.keep:
            self.out.append(data)
        elif data.strip():
            self.line(" ".join(data.split()))

    def handle_comment(self, data):
        self.line(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.line(f"<!{decl}>")

    def handle_entityref(self, name):
        self.out.append(f"&{name};") if self.keep else self.line(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};") if self.keep else self.line(f"&#{name};")


def html_minifier(html_file: Path, action: Literal["minify", "beautify"] = "minify", indent: int = 2) -> dict:
    """Minify an HTML file (drop comments and the whitespace between tags, keep <pre>,
    <script> and <style> intact) or beautify it with one tag per line and
    indentation.
    """
    text = html_file.read_text(encoding="utf-8-sig", errors="replace")
    before = len(text.encode("utf-8"))
    if action == "minify":
        protected = {}

        def stash(m):
            key = f"\x00{len(protected)}\x00"
            protected[key] = m.group(0)
            return key

        work = re.sub(r"<(pre|textarea|script|style)\b[^>]*>.*?</\1>", stash, text, flags=re.S | re.I)
        work = re.sub(r"<!--(?!\[if).*?-->", "", work, flags=re.S)
        work = re.sub(r">\s+<", "> <", work)
        work = re.sub(rf"({BLOCK_TAG}) <", r"<", work)
        work = re.sub(rf"> ({BLOCK_TAG})", r">", work)
        work = re.sub(r"\s{2,}", " ", work)
        work = re.sub(r"\s+>", ">", work)
        for key, value in protected.items():
            work = work.replace(key, value)
        result = work.strip()
        out = html_file.with_name(f"{html_file.stem}.min.html")
    else:
        parser = Pretty(max(1, min(indent, 8)))
        parser.feed(text)
        parser.close()
        result = "\n".join(parser.out)
        out = html_file.with_name(f"{html_file.stem}_pretty.html")
    out.write_text(result + "\n", encoding="utf-8")
    after = out.stat().st_size
    return {
        "file": out,
        "before_bytes": before,
        "after_bytes": after,
        "change": f"{(after / before - 1) * 100:+.1f}%" if before else "n/a",
    }
