"""The finish step: a CadQuery object is exported as a model; every other result passes through untouched."""

import subprocess
import sys

import pytest

from sandbox.runner import finish_result, is_cadquery


def test_plain_values_pass_through():
    assert finish_result("text") == "text"
    assert finish_result({"a": 1}) == {"a": 1}
    assert finish_result(None) is None


def test_cadquery_result_is_exported(tmp_path):
    cq = pytest.importorskip("cadquery")
    out = finish_result(cq.Workplane().box(1, 2, 3), tmp_path)
    assert set(out) == {"stl", "step", "preview", "meta"}
    assert (tmp_path / "model.stl").exists()


def test_shapes_and_assemblies_are_cadquery():
    cq = pytest.importorskip("cadquery")
    box = cq.Workplane().box(1, 1, 1)
    assert is_cadquery(box) and is_cadquery(box.val()) and is_cadquery(cq.Assembly().add(box))
    assert not is_cadquery(cq.Vector(1, 2, 3))  # a CadQuery type, but not a shape


def test_plain_value_does_not_import_cadquery():
    # in a fresh interpreter: a converter's result must not pay CadQuery's import
    code = "import sys; from sandbox.runner import finish_result; finish_result(3); print('cadquery' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
