from pathlib import Path


def size_of_file(path: Path, x: int) -> dict[Path, int]:
    return {"path": path, "number": x}
