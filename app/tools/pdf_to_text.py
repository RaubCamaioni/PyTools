from pathlib import Path
import difflib
import pymupdf
from dataclasses import dataclass
import json


@dataclass
class Word:
    bbox: tuple[float, float, float, float]
    word: str
    page: pymupdf.Page
    index: tuple[int, int, int]

    def __hash__(self):
        return hash(self.word)

    def __eq__(self, other: "Word"):
        if isinstance(other, Word):
            return self.word == other.word
        return NotImplemented

    def __str__(self):
        return self.word

    def heighlight(self, color=(1, 1, 0)):
        annot = self.page.add_highlight_annot(self.bbox)
        annot.set_colors(stroke=color)
        annot.update()


def pdf_text_generator(pdf: Path):
    for page in pdf:
        for word in page.get_text("words"):
            yield Word(bbox=word[:4], page=page, word=word[4], index=word[4:])


def page_text_generator(pdf: Path, index: int):
    page = pdf[index]
    for word in page.get_text("words"):
        yield Word(bbox=word[:4], page=page, word=word[4], index=word[4:])


def page_vector_generator(pdf: Path, index: int):
    page: pymupdf.Page = pdf[index]
    for vector in page.get_drawings():
        yield vector


def line_difference(words_a: list[Word], words_b: list[Word]):
    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    differing_lines = []

    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == "replace":
            for word in words_a[a0:a1]:
                word.heighlight()
                differing_lines.append(rf"{opcode} | {word}")

            for word in words_b[b0:b1]:
                word.heighlight()
                differing_lines.append(rf"{opcode} | {word}")

        if opcode == "insert":
            for word in words_b[b0:b1]:
                word.heighlight(color=(0, 0, 1))
                differing_lines.append(rf"{opcode} | {word}")

        if opcode == "delete":
            for word in words_a[a0:a1]:
                word.heighlight(color=(0, 1, 0))
                differing_lines.append(rf"{opcode} | {word}")

    return differing_lines


def pdf_to_text(file_a: Path, file_b: Path):
    pdf_a = pymupdf.open(file_a)
    pdf_b = pymupdf.open(file_b)
    # text_a = list(pdf_text_generator(pdf_a))
    # text_b = list(pdf_text_generator(pdf_b))
    text_a = list(page_text_generator(pdf_a, 51))
    text_b = list(page_text_generator(pdf_b, 53))
    diff = line_difference(text_a, text_b)

    from itertools import islice
    from collections import defaultdict

    dd_a = defaultdict(lambda: 1)
    for path in islice(page_vector_generator(pdf_a, 64), None):
        for x in path.get("items", {}):
            dd_a[x[0]] = dd_a[x[0]] + 1

    dd_b = defaultdict(lambda: 1)

    page: pymupdf.Page = list(pdf_b)[66]
    shape: pymupdf.Shape = page.new_shape()

    for path in islice(page_vector_generator(pdf_b, 66), None):
        for x in path["items"]:
            dd_b[x[0]] = dd_b[x[0]] + 1

            if x[0] == "c":
                shape.draw_bezier(*x[1:5])

        shape.finish(
            fill=path["fill"],  # fill color
            color=(1, 0, 0),  # line color
            lineCap=1,  # how line ends should look like
            closePath=path["closePath"],
            width=1,  # line width
            stroke_opacity=1,  # same value for both
            fill_opacity=1,  # opacity parameters
        )

    shape.commit()

    print(dd_a)
    print(dd_b)

    pdf_a.save("highlighted-file-a.pdf")
    pdf_b.save("highlighted-file-b.pdf")

    # print(list(page_vector_generator(pdf_a, 51)))
    # print((page_vector_generator(pdf_b, 53)))

    return []
