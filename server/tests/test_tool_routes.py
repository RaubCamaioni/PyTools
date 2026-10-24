import asyncio
import dataclasses
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.models import tools as db
from app.routes import tools as tools_routes
from sandboxcore.host import Outcome, Sandbox, SandboxBusy, SandboxUnavailable
from sandboxcore.host.podman import RunResult
from sandboxcore.testing import UnsandboxedRunner

# what the sandbox returns when a tool returned a CadQuery object: the export dict (see sandbox/export.py)
BUILD = {
    "stl": "model.stl",
    "step": "model.step",
    "preview": "preview.svg",
    "meta": {"size_mm": [30, 20, 10], "volume_mm3": 6000.0, "area_mm2": 2200.0, "solids": 1},
}


def built(**meta):
    return RunResult(Outcome.OK, results={**BUILD, "meta": {**BUILD["meta"], **meta}})


class StubRunner:
    """Stands in for PodmanRunner under a real Sandbox: a run returns `result`, while --inspect runs the
    real Python runtime locally (sandboxcore.testing), so uploads are inspected as in production."""

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

    async def run(self, tool, run_dir, on_line=None, runtime_args=()):
        if "--inspect" in runtime_args:
            return await UnsandboxedRunner(tools_routes.ENVIRONMENT.sandbox).run(tool, run_dir, runtime_args=runtime_args)
        self.calls.append((tool, run_dir))
        self.on_line = on_line
        if self.raise_:
            raise self.raise_
        if self.result.outcome is Outcome.OK and isinstance(self.result.results, dict):
            # a real run leaves a model's export in its run directory and names it there
            results = dict(self.result.results)
            for key in ("stl", "step", "preview"):
                if results.get(key) in ("model.stl", "model.step", "preview.svg"):
                    path = Path(run_dir) / results[key]
                    path.write_text(f"<{results[key]}>")
                    results[key] = path
            return RunResult(Outcome.OK, results=results)
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
    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=runner))
    return TestClient(app)


def test_code_view_shows_the_trailing_newline_as_an_empty_last_line(monkeypatch, public_tool):
    code = "# tag\n\n\ndef byte_converter() -> int:\n    return 1\n"
    monkeypatch.setattr(db, "get_tool_by_id", lambda session, id: db.Tool(id=8, name="t", code=code, public=True, tags=[]))
    page = client(monkeypatch, StubRunner()).get("/tool/8").text
    # the view's text ends in two newlines, so Prism numbers an empty line 6; the status bar counts 5 like vim
    assert "    return 1\n\n</code>" in page and ">5L<" in page


def test_code_view_without_a_trailing_newline_adds_none(monkeypatch, public_tool):
    page = client(monkeypatch, StubRunner()).get("/tool/8").text  # the fixture's code has no newline at all
    assert "return 1</code>" in page and ">1L<" in page


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

    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=SlowStartRunner(available=False)))
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


def test_tool_page_names_the_author_as_alias_and_id(monkeypatch, tmp_path):
    import dataclasses

    monkeypatch.setattr(
        db,
        "get_tool_by_id",
        lambda session, id: db.Tool(id=8, name="t", code="", arguments={}, public=True, annonymous=False, user_id=49600918, tags=[]),
    )
    monkeypatch.setattr(tools_routes.db_tools, "get_user_by_id", lambda session, id: db.User(id=49600918, alias="rob"))
    env = tools_routes.ENVIRONMENT
    monkeypatch.setattr(tools_routes, "ENVIRONMENT", dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path)))
    page = client(monkeypatch, StubRunner()).get("/tool/8").text
    assert "rob#49600918" in page
    assert page.index("t.py</span>") < page.index("rob#49600918") < page.index('id="vim-mode"')  # status bar, after the name
    assert "vim t.py" not in page  # no heading above the code


def test_anonymous_tool_hides_the_alias_and_the_id(monkeypatch, tmp_path):
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
    assert "anonymous#00000000" in page and "rob#" not in page and "49600918" not in page


def test_every_page_carries_the_version_tag(monkeypatch, public_tool):
    from app import TEMPLATES

    monkeypatch.setitem(TEMPLATES.env.globals, "commit_sha", "8cb5eba1234567890")
    monkeypatch.setitem(TEMPLATES.env.globals, "app_version", "0.2.0")
    c = client(monkeypatch, StubRunner())
    for path in ("/", "/tool/8", "/privacy-policy"):
        page = c.get(path).text
        assert 'id="version-tag"' in page and ">v0.2.0+8cb5eba<" in page, path
        assert "github.com/RaubCamaioni/PyTools/commit/8cb5eba1234567890" in page


class FileRunner(StubRunner):
    """A run that writes `files` into its run directory and returns their paths, as a tool would."""

    def __init__(self, files):
        super().__init__()
        self.files = files

    async def run(self, tool, run_dir, on_line=None, runtime_args=()):
        self.calls.append((tool, run_dir))
        for name, data in self.files.items():
            (run_dir / name).write_bytes(data)
        return RunResult(Outcome.OK, results={name: run_dir / name for name in self.files})


def run_and_get_urls(c):
    """Run the tool (JSON response): each returned file comes back as its download URL."""
    r = c.post("/tool/8")
    assert r.status_code == 200, r.text
    return json.loads(r.text)


# `with` keeps one event loop across requests, as in production: a client without it gives each request its
# own loop, and closing it cancels the run's cleanup task, which removes the run directory at once
def test_download_serves_a_file_the_run_returned(monkeypatch, public_tool):
    with client(monkeypatch, FileRunner({"qr_code.png": b"png"})) as c:
        url = run_and_get_urls(c)["qr_code.png"]
        assert re.fullmatch(r"/download/[A-Za-z0-9_-]{32}/qr_code.png", url)
        r = c.get(url)
    assert r.status_code == 200 and r.content == b"png"
    assert "qr_code.png" in r.headers["content-disposition"]


def test_image_preview_is_served_inline_with_its_media_type(monkeypatch, public_tool):
    files = {"qr_code.png": b"png", "data.csv": b"a,b", "song.mp3": b"mp3", "doc.pdf": b"pdf"}
    with client(monkeypatch, FileRunner(files)) as c:
        urls = run_and_get_urls(c)
        for name, media_type in (("qr_code.png", "image/png"), ("song.mp3", "audio/mpeg"), ("doc.pdf", "application/pdf")):
            r = c.get(urls[name] + "?preview=1")
            assert r.status_code == 200 and r.headers["content-type"] == media_type, name
            assert r.headers["content-disposition"].startswith("inline")
        # preview only changes how images are served; anything else stays a download
        r = c.get(urls["data.csv"] + "?preview=1")
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["content-disposition"].startswith("attachment")


def test_download_of_an_expired_result_is_404_with_a_reason(monkeypatch, public_tool):
    r = client(monkeypatch, StubRunner()).get("/download/" + "x" * 32 + "/qr_code.png")
    assert r.status_code == 404 and "expired" in r.json()["detail"]


def test_only_files_inside_a_kept_run_are_served(monkeypatch, public_tool, tmp_path):
    (tmp_path.parent / "elsewhere.txt").write_text("x")
    with client(monkeypatch, FileRunner({"out.txt": b"o"})) as c:
        url = run_and_get_urls(c)["out.txt"]
        assert c.get(url).status_code == 200  # the run is kept: the refusals below are not just expiry
        run = url.split("/")[2]
        for name in ["../../elsewhere.txt", "%2E%2E/%2E%2E/elsewhere.txt", "args.json", "byte_converter.py", "/etc/passwd"]:
            assert c.get(f"/download/{run}/{name}").status_code == 404, name


def test_a_returned_path_outside_the_run_is_refused(monkeypatch, public_tool, tmp_path):
    (tmp_path.parent / "secret.txt").write_text("SESSION_KEY=x")
    stub = StubRunner(RunResult(Outcome.OK, results={"f": tmp_path.parent / "secret.txt"}))
    r = client(monkeypatch, stub).post("/tool/8")
    assert r.json() == {"detail": "Tool returned a path that is not a file it made"}


def test_tool_page_downloads_results_in_place(monkeypatch, public_tool):
    page = client(monkeypatch, StubRunner()).get("/tool/8").text
    assert """closest('a[href^="/download/"]')""" in page and "event.preventDefault()" in page


def create_tool(user_id: int, name: str, code) -> db.Tool:
    """A tool made the way an upload makes it: accept_source, prepare_source, then Sandbox.inspect with
    the real Python runtime run locally (sandboxcore.testing). Refusals raise HTTPException as the route does."""
    from unittest import mock

    from fastapi import HTTPException

    from app.routes import upload as upload_routes
    from sandboxcore.host import SourceError, accept_source

    config = tools_routes.ENVIRONMENT.sandbox
    try:
        source = accept_source(code.encode() if isinstance(code, str) else code, f"{name}.py")
    except SourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with mock.patch.object(tools_routes, "sandbox", Sandbox(config, runner=UnsandboxedRunner(config))):
        return asyncio.run(upload_routes._create_tool(user_id, source))


def test_a_run_that_returns_a_model_shows_the_viewer(monkeypatch, public_tool):
    runner = StubRunner(built())
    c = client(monkeypatch, runner)
    body = json.loads(c.post("/tool/8").text)
    run = "/download/" + Path(runner.calls[-1][1]).name  # the run's id is its directory's name
    assert body["stl"] == f"{run}/model.stl" and body["step"] == f"{run}/model.step"
    assert body["meta"]["size_mm"] == [30, 20, 10]
    page = c.post("/tool/8", headers={"HX-Request": "true"}).text
    run = "/download/" + Path(runner.calls[-1][1]).name
    assert f'<stl-viewer url="{run}/model.stl">' in page
    assert "30 &times; 20 &times; 10 mm" in page and "6.00 cm&sup3;" in page
    assert f'href="{run}/model.step" download="byte_converter.step"' in page


def test_a_model_with_malformed_measurements_is_an_export_error(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(built(solids="many")))
    page = c.post("/tool/8", headers={"HX-Request": "true"}).text
    assert "Export Error" in page and "<stl-viewer" not in page


def test_a_dict_that_is_not_a_model_renders_as_before(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(RunResult(Outcome.OK, results={"stl": "not a file", "other": 1})))
    page = c.post("/tool/8", headers={"HX-Request": "true"}).text
    assert "<stl-viewer" not in page and "not a file" in page
