# markdown, text, epub, ebook, converter

from pathlib import Path
from typing import Literal
import html
import re
import markdown
from ebooklib import epub


def markdown_to_epub(
    text_file: Path,
    title: str = "My Book",
    author: str = "Unknown",
    input_format: Literal["markdown", "plain_text", "html"] = "markdown",
    split_chapters_on: Literal["heading_1", "heading_2", "no_split"] = "heading_1",
) -> Path:
    """Build an EPUB ebook from a Markdown, plain text or HTML file. Level-1 (or
    level-2) headings become chapters and the table of contents.
    """
    text = text_file.read_text(encoding="utf-8-sig", errors="replace")
    if input_format == "plain_text":
        body = "".join(f"<p>{html.escape(p.strip())}</p>\n" for p in re.split(r"\n\s*\n", text) if p.strip())
    elif input_format == "html":
        body = text
    else:
        body = markdown.markdown(text, extensions=["extra", "sane_lists", "toc"])

    level = {"heading_1": "h1", "heading_2": "h2"}.get(split_chapters_on)
    chapters: list[tuple[str, str]] = []
    if level:
        pieces = re.split(rf"(?=<{level}[ >])", body)
        for piece in pieces:
            if not piece.strip():
                continue
            m = re.match(rf"<{level}[^>]*>(.*?)</{level}>", piece, re.S)
            chapters.append((re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else "Chapter", piece))
    if not chapters:
        chapters = [(title, body)]

    book = epub.EpubBook()
    book.set_identifier(f"pywebtools-{abs(hash((title, author, len(text)))):x}")
    book.set_title(title.strip() or text_file.stem)
    book.set_language("en")
    book.add_author(author.strip() or "Unknown")
    style = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content="body{font-family:serif;line-height:1.5}h1,h2{font-family:sans-serif}pre{white-space:pre-wrap}",
    )
    book.add_item(style)

    items = []
    for i, (name, content) in enumerate(chapters, 1):
        chapter = epub.EpubHtml(title=name[:120], file_name=f"chapter_{i:03d}.xhtml", lang="en")
        chapter.content = f"<html><head><title>{html.escape(name)}</title></head><body>{content}</body></html>"
        chapter.add_item(style)
        book.add_item(chapter)
        items.append(chapter)

    book.toc = items
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + items
    out = text_file.with_suffix(".epub")
    epub.write_epub(str(out), book)
    return out
