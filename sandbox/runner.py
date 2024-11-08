from typing import List, Any, Dict, Callable
from pathlib import Path
import importlib.util


def main(file: Path, args: List = None, kwargs: Dict[str, Any] = None) -> Any:

    args = args or []
    kwargs = kwargs or {}

    module_name = file.stem
    spec = importlib.util.spec_from_file_location(module_name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, module_name):
        raise ValueError(f"can not find function: {module_name}")

    func: Callable[[Any], Any] = getattr(module, module_name, None)

    return func(*args, **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str)
    args = parser.parse_args()

    main(Path(args.file))
