import pytest
from fastapi import HTTPException

from app.models import tools as db


def source(line: str) -> str:
    return "# tag\n\n" + line + "\n\n\ndef demo(value: int = 1) -> int:\n    return value\n"


def test_line_at_the_limit_is_accepted():
    tool = db.create_tool(1, "demo", source("x = 1  " + "#" * (db.MAX_LINE_LENGTH - 7)))
    assert tool.name == "demo" and tool.arguments == {"value": ("int", "1")}


def test_line_over_the_limit_is_rejected_with_its_number():
    line = "x = '" + "a" * db.MAX_LINE_LENGTH + "'"
    with pytest.raises(HTTPException) as info:
        db.create_tool(1, "demo", source(line))
    assert info.value.status_code == 400
    assert info.value.detail.startswith(f"Line Too Long: line 3 has {len(line)} characters")


def test_length_check_runs_before_syntax_check():
    # a long line that is also invalid python reports the length problem, the easier one to fix
    with pytest.raises(HTTPException) as info:
        db.create_tool(1, "demo", source("def (" + "a" * 130))
    assert "Line Too Long" in info.value.detail


@pytest.mark.parametrize("name", ["byte_converter", "sha256"])
def test_shipped_tools_pass(name):
    from pathlib import Path

    code = (Path(__file__).resolve().parents[2] / "tools" / f"{name}.py").read_text(encoding="utf-8")
    assert db.create_tool(1, name, code).name == name
