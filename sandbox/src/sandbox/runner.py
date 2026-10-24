"""The sandbox entrypoint: sandboxcore's Python runner with a finish step for CadQuery results.

A tool that returns a CadQuery object (a Workplane, Shape or Assembly) is a model: `finish_result` exports it
to STL, STEP, a preview and its measurements (`sandbox.export`), and that dict becomes the run's result. Any
other result passes through untouched, and CadQuery is never imported for it.
"""

from pathlib import Path
from typing import Any

from sandboxcore.python.runner import main as run_tool

# a CadQuery object's type lives in one of these packages; anything else is not one, without importing CadQuery
CADQUERY_MODULES = ("cadquery", "OCP")


def is_cadquery(value: Any) -> bool:
    if not type(value).__module__.startswith(CADQUERY_MODULES):
        return False
    import cadquery as cq

    return isinstance(value, (cq.Workplane, cq.Shape, cq.Assembly))


def finish_result(result: Any, workdir: Path | None = None) -> Any:
    if not is_cadquery(result):
        return result
    from sandbox.export import export_model

    return export_model(result, workdir)


def main():
    run_tool(finish=finish_result, finish_label="Export Error")


if __name__ == "__main__":
    main()
