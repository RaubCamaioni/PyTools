# html, text, markdown, document, converter

from pathlib import Path
from typing import Literal
from html.parser import HTMLParser
import re

BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header", "footer", "pre", "blockquote", "hr", "table"}
SKIP = {"script", "style", "head", "noscript", "template"}


class Extractor(HTMLParser):
    def __init__(self, markdown: bool):
        super().__init__(convert_charrefs=True)
        self.markdown = markdown
        self.parts: list[str] = []
        self.skip = 0
        self.href = None
        self.list_depth = 0
        self.ordered: list[bool] = []
        self.counters: list[int] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP:
            self.skip += 1
            return
        if tag in ("ul", "ol"):
            self.ordered.append(tag == "ol")
            self.counters.append(0)
        if tag in BLOCK:
            self.parts.append("\n")
        if not self.markdown:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "li":
            if self.ordered and self.ordered[-1]:
                self.counters[-1] += 1
                self.parts.append("  " * (len(self.ordered) - 1) + f"{self.counters[-1]}. ")
            else:
                self.parts.append("  " * (len(self.ordered) - 1) + "- ")
        elif tag in ("strong", "b"):
            self.parts.append("**")
        elif tag in ("em", "i"):
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "a":
            self.href = a.get("href")
            self.parts.append("[")
        elif tag == "img":
            self.parts.append(f"![{a.get('alt', '')}]({a.get('src', '')})")
        elif tag == "hr":
            self.parts.append("---\n")
        elif tag == "blockquote":
            self.parts.append("> ")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag in ("ul", "ol") and self.ordered:
            self.ordered.pop()
            self.counters.pop()
        if tag in BLOCK:
            self.parts.append("\n")
        if not self.markdown:
            return
        if tag in ("strong", "b"):
            self.parts.append("**")
        elif tag in ("em", "i"):
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "a":
            self.parts.append(f"]({self.href or ''})")
            self.href = None
        elif tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(re.sub(r"[ \t\r\n]+", " ", data))


def html_to_text(html_file: Path, output: Literal["plain_text", "markdown"] = "plain_text") -> Path:
    """Strip the tags from an HTML file, producing plain text or simple Markdown (headings, lists, links, emphasis)."""
    text = html_file.read_text(encoding="utf-8", errors="replace")
    parser = Extractor(markdown=output == "markdown")
    parser.feed(text)
    result = "".join(parser.parts)
    result = re.sub(r"[ \t]+\n", "\n", result)
    result = re.sub(r"\n[ \t]+", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result).strip() + "\n"
    out = html_file.with_suffix(".md" if output == "markdown" else ".txt")
    out.write_text(result, encoding="utf-8")
    return out
