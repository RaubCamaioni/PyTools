# text, converter

from pathlib import Path


def lower_case_text(input: Path) -> Path:
    output = Path("output.txt")

    with open(input, "r") as f:
        text = f.read()

    with open(output, "w") as f:
        f.write(text.lower())

    return output
