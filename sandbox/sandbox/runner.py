from typing import Any, Callable
from functools import partial
from pathlib import Path
import importlib.util
import serializer
import traceback
import sys
import os


def main(file: Path, workdir: Path) -> Any:
    os.chdir(workdir)

    with open("args.json", "r") as f:
        args = serializer.load(f)

    module_name = file.stem
    spec = importlib.util.spec_from_file_location(module_name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, module_name):
        raise ValueError(f"no function named: {module_name}")

    func: Callable[[Any], Any] = getattr(module, module_name, None)

    try:
        results = partial(func, **args)()
    except Exception as e:
        _, _, exc_traceback = sys.exc_info()
        frames = traceback.extract_tb(exc_traceback)

        trace = []
        for frame in frames:
            trace.append(f"  {frame.name}: {frame.lineno}")
        trace = "\n".join(trace)
        results = f"Runtime Error: {file.stem} {type(e).__name__}\n{trace}"

        print(results)

    with open("result.json", "w") as f:
        serializer.dump(results, f)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str, required=True)
    parser.add_argument("--workdir", "-w", type=str, required=True)
    args = parser.parse_args()

    file = Path(args.file)
    workdir = Path(args.workdir)

    main(file, workdir)
