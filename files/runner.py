from typing import Any, Callable
from functools import partial
from pathlib import Path
import importlib.util


def main(tool: Path, kwargs) -> Any:
    function_name = tool.stem
    spec = importlib.util.spec_from_file_location(function_name, tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        raise ValueError(f"no function named: {function_name}")

    func: Callable[[Any], Any] = getattr(module, function_name, None)

    try:
        return partial(func, **kwargs)()
    except Exception as e:
        return f"Runtime Exception: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", "-f", type=str, required=True)
    args, unknown_args = parser.parse_known_args()

    tool = Path(args.tool)

    kwargs = {k[2:]: v for k, v in zip(unknown_args[::2], unknown_args[1::2])}

    print(f"Running File: {tool}")
    print(f"kwargs: {kwargs}")
    result = main(tool, kwargs)

    print(repr(result))
