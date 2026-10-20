# text, lorem, placeholder, generator

from typing import Literal
import random

WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore "
    "et dolore magna aliqua enim ad minim veniam quis nostrud exercitation ullamco laboris nisi aliquip "
    "ex ea commodo consequat duis aute irure in reprehenderit voluptate velit esse cillum fugiat nulla "
    "pariatur excepteur sint occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim "
    "id est laborum curabitur pretium tincidunt lacus nulla gravida orci a odio nullam varius turpis "
    "et commodo pharetra est eros bibendum elit nec luctus magna felis sollicitudin mauris integer"
).split()


def sentence() -> str:
    words = " ".join(random.choice(WORDS) for _ in range(random.randint(6, 14)))
    return words[0].upper() + words[1:] + "."


def paragraph() -> str:
    return " ".join(sentence() for _ in range(random.randint(4, 8)))


def lorem_ipsum(
    count: int = 3,
    unit: Literal["paragraphs", "sentences", "words"] = "paragraphs",
    start_with_lorem: Literal["yes", "no"] = "yes",
) -> str:
    """Generate placeholder Lorem Ipsum text as paragraphs, sentences or words."""
    count = max(1, min(count, 500))
    head = "Lorem ipsum dolor sit amet, consectetur adipiscing elit"

    if unit == "words":
        words = [random.choice(WORDS) for _ in range(count)]
        if start_with_lorem == "yes":
            words = (head.replace(",", "").split() + words)[:count]
        return " ".join(words)

    if unit == "sentences":
        text = " ".join(sentence() for _ in range(count))
    else:
        text = "\n\n".join(paragraph() for _ in range(count))

    if start_with_lorem == "yes":
        text = head + ", " + text[0].lower() + text[1:]
    return text
