from pathlib import Path


def multi_modal_return() -> tuple[Path, str, dict]:
    file = Path("simple_file.txt")

    with open(file, "w") as f:
        f.write("this is a simple file")

    dictionary = {"a": "dog", "b": {"c": file}}
    return {"simple", "set"}
