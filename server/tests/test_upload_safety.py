"""Uploads never choose where they land on the host, and only a tool's owner can replace its code."""

import dataclasses
import json

import pytest
from pathlib import Path
from sqlmodel import Session

from app.models import tools as db
from app.routes import tools as tools_routes
from app.routes import upload as upload_routes
from app.utility.podman_runner import Outcome, RunResult

from tests.test_tool_routes import StubRunner, client

CODE = b"# tag\n\n\ndef demo(value: int = 1) -> int:\n    return value\n"


@pytest.fixture
def path_tool(monkeypatch, tmp_path):
    code = "# tag\n\nfrom pathlib import Path\n\n\ndef demo(data: Path) -> str:\n    return data.read_text()\n"
    tool = db.Tool(id=9, name="demo", code=code, arguments={"data": ("Path", None)}, public=True, tags=[])
    monkeypatch.setattr(db, "get_tool_by_id", lambda session, id: tool)
    env = tools_routes.ENVIRONMENT
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    monkeypatch.setattr(
        tools_routes,
        "ENVIRONMENT",
        dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=run_dir)),
    )
    return run_dir


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("../../escaped.txt", "escaped.txt"),
        ("/tmp/escaped.txt", "escaped.txt"),
        ("a/../../b.txt", "b.txt"),
        ("..\..\win.txt", "win.txt"),
        ("..", "data"),
        (".bashrc", "bashrc"),
        ("args.json", "args.json"),
        ("demo.py", "demo.py"),
        ("result.json", "result.json"),
        ("photo $(id).PNG", "photo __id_.PNG"),
    ],
)
def test_an_upload_lands_in_its_own_input_directory(monkeypatch, path_tool, filename, expected):
    seen = {}

    async def run(tool, run_dir, on_line=None):
        args = json.loads((run_dir / "args.json").read_text())
        seen["path"] = Path(args["data"]["__path__"])
        seen["inputs"] = (run_dir / "inputs" / "data").resolve()
        seen["code"] = (run_dir / tool.name).read_text()
        seen["content"] = seen["path"].read_bytes()
        return RunResult(Outcome.OK, results="ok")

    runner = StubRunner()
    runner.run = run
    r = client(monkeypatch, runner).post("/tool/9", files={"data": (filename, b"payload")})
    assert r.status_code == 200
    # the tool keeps a readable name for its output, but the directory is the server's choice
    assert seen["path"].resolve().parent == seen["inputs"] and seen["path"].name == expected
    assert seen["content"] == b"payload"
    assert seen["code"].startswith("# tag")  # the tool's own file and the control files are untouched
    assert not Path("/tmp/escaped.txt").exists() and not (path_tool.parent / "escaped.txt").exists()


@pytest.fixture
def accounts():
    with Session(db.engine) as session:
        for user in (db.User(id=501, alias="owner"), db.User(id=502, alias="other"), db.User(id=503, alias="gone", banned=True)):
            session.merge(user)
        session.merge(db.Tool(id=601, name="demo", code="# tag\n\n\ndef demo() -> int:\n    return 0\n", user_id=501, tags=[]))
        session.commit()
    yield
    with Session(db.engine) as session:
        for model, id in ((db.Tool, 601), (db.User, 501), (db.User, 502), (db.User, 503)):
            row = session.get(model, id)
            if row is not None:
                session.delete(row)
        session.commit()


def stored_code():
    with Session(db.engine) as session:
        return session.get(db.Tool, 601).code


def as_user(monkeypatch, user):
    monkeypatch.setattr(upload_routes, "session_user", lambda request: user)
    return client(monkeypatch, StubRunner())


def test_another_user_cannot_overwrite_a_tool(monkeypatch, accounts):
    before = stored_code()
    r = as_user(monkeypatch, db.User(id=502, alias="other")).post("/manage/tool/update/601", files={"file": ("demo.py", CODE)})
    assert r.status_code == 404 and stored_code() == before


def test_an_admin_flag_in_the_cookie_grants_nothing(monkeypatch, accounts):
    before = stored_code()
    forged = db.User(id=502, alias="other", admin=True)
    r = as_user(monkeypatch, forged).post("/manage/tool/update/601", files={"file": ("demo.py", CODE)})
    assert r.status_code == 404 and stored_code() == before


def test_the_owner_can_update_their_tool(monkeypatch, accounts):
    r = as_user(monkeypatch, db.User(id=501, alias="owner")).post("/manage/tool/update/601", files={"file": ("demo.py", CODE)})
    assert r.status_code == 200 and "value: int = 1" in stored_code()


def test_a_banned_user_cannot_upload_even_with_a_stale_cookie(monkeypatch, accounts):
    stale = db.User(id=503, alias="gone", banned=False)
    r = as_user(monkeypatch, stale).post("/manage/tool/upload", files={"file": ("demo.py", CODE)})
    assert r.status_code == 403


def test_uploading_requires_login(monkeypatch, accounts):
    r = as_user(monkeypatch, None).post("/manage/tool/update/601", files={"file": ("demo.py", CODE)})
    assert r.status_code == 404 and "value" not in stored_code()
