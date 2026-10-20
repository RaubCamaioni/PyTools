import asyncio
import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.models import tools as db
from app.routes import tools as tools_routes
from app.utility.podman_runner import Outcome, RunResult, SandboxBusy, SandboxUnavailable


class StubRunner:
    def __init__(self, result=None, raise_=None, available=True):
        self.result, self.raise_, self.available = result, raise_, available
        self.unavailable_reason = None if available else "self-test failed"
        self.calls = []
        self.on_line = None

    async def start(self):
        pass

    def start_in_background(self):
        asyncio.create_task(self.start())

    async def stop(self):
        pass

    async def run(self, tool, run_dir, on_line=None):
        self.calls.append((tool, run_dir))
        self.on_line = on_line
        if self.raise_:
            raise self.raise_
        return self.result


@pytest.fixture
def public_tool(monkeypatch, tmp_path):
    monkeypatch.setattr(
        db,
        "get_tool_by_id",
        lambda session, id: db.Tool(
            id=8, name="byte_converter", code="def byte_converter(): return 1", arguments={}, public=True, tags=[]
        ),
    )
    # SandboxConfig is frozen: swap the whole ENVIRONMENT the routes module sees
    env = tools_routes.ENVIRONMENT
    monkeypatch.setattr(
        tools_routes,
        "ENVIRONMENT",
        dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path)),
    )


def client(monkeypatch, runner):
    monkeypatch.setattr(tools_routes, "runner", runner)
    return TestClient(app)


def test_run_tool_ok_renders_results(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(RunResult(Outcome.OK, results="0x68 0x69")))
    r = c.post("/tool/8")
    assert r.status_code == 200 and json.loads(r.text) == "0x68 0x69"


def test_run_tool_timeout_message_htmx(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(RunResult(Outcome.TIMEOUT, message="Tool exceeded the 10 second limit")))
    r = c.post("/tool/8", headers={"HX-Request": "true"})
    assert r.status_code == 200 and "Tool exceeded the 10 second limit" in r.text


def test_run_tool_malformed_result_renders_failure(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(RunResult(Outcome.CRASHED, message="Tool failed to run", stderr_tail="boom")))
    r = c.post("/tool/8")
    assert r.status_code == 200 and r.json() == {"detail": "Tool failed to run"}


def test_run_tool_busy_is_503(monkeypatch, public_tool):
    r = client(monkeypatch, StubRunner(raise_=SandboxBusy())).post("/tool/8")
    assert r.status_code == 503 and r.json()["detail"] == "Server busy, try again"


def test_run_tool_unavailable_returns_503_without_slot(monkeypatch, public_tool):
    stub = StubRunner(raise_=SandboxUnavailable(), available=False)
    r = client(monkeypatch, stub).post("/tool/8")
    assert r.status_code == 503 and r.json()["detail"] == "Sandbox unavailable"
    assert stub.calls == []  # route checks runner.available before writing files or running


def test_lifespan_does_not_wait_for_runner_start(monkeypatch):
    import time

    class SlowStartRunner(StubRunner):
        async def start(self):
            await asyncio.sleep(3)

    monkeypatch.setattr(tools_routes, "runner", SlowStartRunner(available=False))
    started = time.monotonic()
    with TestClient(app) as c:
        assert c.get("/healthz").status_code == 503
    assert time.monotonic() - started < 2  # pages are served while the sandbox is still starting


def test_stylesheet_urls_are_versioned(monkeypatch, public_tool):
    import re

    c = client(monkeypatch, StubRunner())
    for path in ("/", "/tool/8"):
        html = c.get(path).text
        # same URL + new content gets served from browser caches; the version query defeats that
        assert re.search(r'/static/output\.css\?v=[0-9a-f]{8,}"', html), path
    assert re.search(r'/static/prism-vim\.css\?v=[0-9a-f]{8,}"', c.get("/tool/8").text)


def test_healthz(monkeypatch):
    assert client(monkeypatch, StubRunner()).get("/healthz").json() == {"sandbox": "ready"}
    r = client(monkeypatch, StubRunner(available=False)).get("/healthz")
    assert r.status_code == 503 and r.json() == {"sandbox": "unavailable", "reason": "self-test failed"}


def test_run_dir_created_under_configured_root(monkeypatch, public_tool, tmp_path):
    stub = StubRunner(RunResult(Outcome.OK, results=None))
    client(monkeypatch, stub).post("/tool/8")
    tool, run_dir = stub.calls[0]
    assert run_dir.parent == tmp_path and tool == run_dir / "byte_converter.py"


def test_tool_page_names_the_author_as_alias_and_id(monkeypatch, public_tool):
    monkeypatch.setattr(tools_routes.db_tools, "get_user_by_id", lambda session, id: db.User(id=49600918, alias="rob"))
    assert "author: rob#49600918" in client(monkeypatch, StubRunner()).get("/tool/8").text


def test_anonymous_tool_hides_the_alias_but_keeps_the_id(monkeypatch, tmp_path):
    import dataclasses

    monkeypatch.setattr(
        db,
        "get_tool_by_id",
        lambda session, id: db.Tool(id=8, name="t", code="", arguments={}, public=True, annonymous=True, user_id=49600918, tags=[]),
    )
    monkeypatch.setattr(tools_routes.db_tools, "get_user_by_id", lambda session, id: db.User(id=49600918, alias="rob"))
    env = tools_routes.ENVIRONMENT
    monkeypatch.setattr(tools_routes, "ENVIRONMENT", dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path)))
    page = client(monkeypatch, StubRunner()).get("/tool/8").text
    assert "author: anonymous#49600918" in page and "rob#" not in page
