# docx, word, find, replace, template, edit

from pathlib import Path
from typing import Literal
from docx import Document


def docx_find_replace(docx: Path, find: str, replace: str = "", case_sensitive: Literal["yes", "no"] = "yes") -> dict:
    """Replace text throughout a Word document (body, tables, headers and footers) while
    keeping the formatting; ideal for filling `{{placeholders}}` in a template.
    """
    if not find:
        return {"error": "Enter the text to find"}
    doc = Document(str(docx))
    count = 0

    def paragraphs():
        for p in doc.paragraphs:
            yield p
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs
        for section in doc.sections:
            for part in (section.header, section.footer):
                yield from part.paragraphs

    needle = find if case_sensitive == "yes" else find.lower()
    for p in paragraphs():
        haystack = p.text if case_sensitive == "yes" else p.text.lower()
        if needle not in haystack:
            continue
        hits = haystack.count(needle)
        done = False
        for run in p.runs:
            run_text = run.text if case_sensitive == "yes" else run.text.lower()
            if needle in run_text:
                run.text = _replace(run.text, find, replace, case_sensitive == "yes")
                done = True
        if not done and p.runs:
            # the match straddles runs: rebuild the text in the first run's style
            new_text = _replace(p.text, find, replace, case_sensitive == "yes")
            for run in p.runs[1:]:
                run.text = ""
            p.runs[0].text = new_text
        count += hits
    out = docx.with_name(f"{docx.stem}_replaced.docx")
    doc.save(str(out))
    return {"file": out, "replacements": count}


def _replace(text: str, find: str, replace: str, case: bool) -> str:
    if case:
        return text.replace(find, replace)
    import re

    return re.sub(re.escape(find), lambda m: replace, text, flags=re.IGNORECASE)
