# html, docx, word, document, converter

from pathlib import Path
from html.parser import HTMLParser
import re
from docx import Document
from docx.shared import Pt


class Builder(HTMLParser):
    def __init__(self, doc: Document):
        super().__init__(convert_charrefs=True)
        self.doc, self.para, self.bold, self.italic, self.skip = doc, None, 0, 0, 0
        self.list_style = None
        self.table, self.row = None, None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.para = self.doc.add_heading("", level=int(tag[1]))
        elif tag in ("p", "div", "blockquote"):
            self.para = self.doc.add_paragraph()
        elif tag == "ul":
            self.list_style = "List Bullet"
        elif tag == "ol":
            self.list_style = "List Number"
        elif tag == "li":
            self.para = self.doc.add_paragraph(style=self.list_style or "List Bullet")
        elif tag in ("b", "strong"):
            self.bold += 1
        elif tag in ("i", "em"):
            self.italic += 1
        elif tag == "br" and self.para is not None:
            self.para.add_run("\n")
        elif tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
            self.table.append(self.row)
        elif tag in ("td", "th") and self.row is not None:
            self.row.append("")
            self.para = None
        elif tag == "pre":
            self.para = self.doc.add_paragraph()
            self.para.style = self.doc.styles["Normal"]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("b", "strong"):
            self.bold = max(0, self.bold - 1)
        elif tag in ("i", "em"):
            self.italic = max(0, self.italic - 1)
        elif tag in ("ul", "ol"):
            self.list_style = None
        elif tag == "table" and self.table:
            width = max(len(r) for r in self.table)
            t = self.doc.add_table(rows=len(self.table), cols=width)
            t.style = "Table Grid"
            for r, row in enumerate(self.table):
                for c, cell in enumerate(row):
                    t.cell(r, c).text = cell.strip()
            self.table = None
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote"):
            self.para = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.row is not None and self.row:
            self.row[-1] += data
            return
        text = re.sub(r"\s+", " ", data)
        if not text.strip():
            return
        if self.para is None:
            self.para = self.doc.add_paragraph()
        run = self.para.add_run(text)
        run.bold, run.italic = bool(self.bold), bool(self.italic)


def html_to_docx(html_file: Path, font_size: int = 11) -> Path:
    """Convert an HTML page into a Word .docx: headings, paragraphs, bold/italic, bullet
    and numbered lists and tables are kept; scripts, styles and layout are dropped.
    """
    doc = Document()
    doc.styles["Normal"].font.size = Pt(max(6, min(font_size, 24)))
    Builder(doc).feed(html_file.read_text(encoding="utf-8-sig", errors="replace"))
    out = html_file.with_suffix(".docx")
    doc.save(str(out))
    return out
