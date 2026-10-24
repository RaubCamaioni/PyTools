"""Uploading a tool that declares a CadQuery return builds it once with its defaults in the sandbox; what that
build produced (thumbnail, measurements, default STL and STEP) is what the listings and the tool page show."""

from pathlib import Path
from urllib.parse import parse_qs
import html
import json

import pytest
from fastapi.testclient import TestClient

from app import ENVIRONMENT
from app.app import app
from app.models import tools as db
from app.routes import tools as tools_routes
from sandboxcore.host import Outcome, Sandbox
from sandboxcore.host.podman import RunResult

from tests.test_auth_routes import github  # noqa: F401  (fixture)
from tests.test_tool_routes import StubRunner, built

MODEL = "# box\n\nimport cadquery as cq\n\n\ndef demo_box(size: float = 10) -> cq.Workplane:\n    return cq.Workplane().box(size, size, size)\n"


class BuildingRunner(StubRunner):
    """Writes the files a real sandbox run would leave in the run directory."""

    async def run(self, tool, run_dir, on_line=None, runtime_args=()):
        if runtime_args:  # --inspect: the real runtime, as StubRunner does it
            return await super().run(tool, run_dir, on_line, runtime_args)
        result = await super().run(tool, run_dir, on_line)
        # the run directory is removed when the test client's loop closes: keep what the app sent
        self.args = json.loads((Path(run_dir) / "args.json").read_text())
        self.saved = {p.relative_to(run_dir).as_posix(): p.read_bytes() for p in Path(run_dir).rglob("*") if p.is_file()}
        if result.outcome is Outcome.OK and isinstance(result.results, dict):
            files = {}
            for key, name in (("stl", "model.stl"), ("step", "model.step"), ("preview", "preview.svg")):
                path = Path(run_dir) / name
                path.write_text(f"<{name}>" if key != "preview" else "<svg>preview</svg>")
                files[key] = path
            result = RunResult(Outcome.OK, results={**result.results, **files})
        return result


@pytest.fixture
def logged_in(monkeypatch, github, tmp_path):  # noqa: F811
    monkeypatch.setattr(tools_routes, "ENVIRONMENT", _env(tools_routes.ENVIRONMENT, tmp_path))
    from app.routes import upload as upload_routes

    monkeypatch.setattr(upload_routes, "ENVIRONMENT", _env(upload_routes.ENVIRONMENT, tmp_path))
    c = TestClient(app)
    page = c.get("/").text
    state = parse_qs(html.unescape(page.split("https://github.com/login/oauth/authorize?")[1].split('"')[0]))["state"][0]
    assert c.get("/auth/github", params={"code": "abc", "state": state}, follow_redirects=False).status_code in (302, 307)
    return c


def _env(env, tmp_path):
    import dataclasses

    return dataclasses.replace(
        env,
        MODELS_DIR=tmp_path / "models",
        sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path / "runs"),
    )


def upload(c, monkeypatch, runner, code=MODEL, name="demo_box.py"):
    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=runner))
    return c.post("/manage/tool/upload", files={"file": (name, code.encode(), "text/x-python")})


def test_upload_validates_and_keeps_the_default_build(monkeypatch, logged_in, tmp_path):
    r = upload(logged_in, monkeypatch, BuildingRunner(built(size_mm=[10, 10, 10])))
    assert r.status_code == 200, r.text
    with db.Session(db.engine) as session:
        model = session.exec(db.select(db.Tool).where(db.Tool.name == "demo_box")).first()
        assert model is not None and model.meta["size_mm"] == [10, 10, 10] and model.preview_svg == "<svg>preview</svg>"
        assert model.kind == "model"
        tool_id = model.id
    assert (tmp_path / "models" / str(tool_id) / "model.stl").read_text() == "<model.stl>"
    assert (tmp_path / "models" / str(tool_id) / "model.step").read_text() == "<model.step>"


def test_upload_that_fails_to_build_is_rejected_and_not_stored(monkeypatch, logged_in):
    failing = StubRunner(RunResult(Outcome.OK, results="Export Error: NotAModel: a model must return a cadquery Workplane"))
    r = upload(logged_in, monkeypatch, failing, code=MODEL.replace("demo_box", "bad_box"), name="bad_box.py")
    assert r.status_code == 400 and "Model Build Failed: Export Error" in r.json()["detail"]
    with db.Session(db.engine) as session:
        assert session.exec(db.select(db.Tool).where(db.Tool.name == "bad_box")).first() is None


def test_a_model_with_a_required_path_is_rejected_before_any_build(monkeypatch, logged_in):
    runner = BuildingRunner()
    code = "from pathlib import Path\nimport cadquery as cq\n\n\ndef with_file(f: Path) -> cq.Workplane:\n    return 1\n"
    r = upload(logged_in, monkeypatch, runner, code=code, name="with_file.py")
    assert r.status_code == 400 and "is a Path" in r.json()["detail"] and runner.calls == []


def test_a_script_with_a_required_path_uploads_without_a_build(monkeypatch, logged_in):
    runner = BuildingRunner()
    code = "from pathlib import Path\n\n\ndef count_bytes(f: Path) -> int:\n    return len(f.read_bytes())\n"
    r = upload(logged_in, monkeypatch, runner, code=code, name="count_bytes.py")
    assert r.status_code == 200, r.text
    assert runner.calls == []  # a script is only inspected
    with db.Session(db.engine) as session:
        tool = session.exec(db.select(db.Tool).where(db.Tool.name == "count_bytes")).first()
        assert tool.kind == "script" and tool.preview_svg == "" and tool.meta == {}


def stored_tool(name):
    with db.Session(db.engine) as session:
        return session.exec(db.select(db.Tool).where(db.Tool.name == name)).first()


def test_a_model_edited_into_a_script_loses_its_build(monkeypatch, logged_in, tmp_path):
    upload(logged_in, monkeypatch, BuildingRunner(built()), code=MODEL.replace("demo_box", "turncoat"), name="turncoat.py")
    tool = stored_tool("turncoat")
    assert tool.kind == "model" and (tmp_path / "models" / str(tool.id) / "model.stl").exists()
    script = "def turncoat(size: float = 10) -> float:\n    return size\n"
    r = logged_in.post(f"/manage/tool/update/{tool.id}", files={"file": ("turncoat.py", script.encode(), "text/x-python")})
    assert r.status_code == 200, r.text
    tool = stored_tool("turncoat")
    assert tool.kind == "script" and tool.preview_svg == "" and tool.meta == {}
    assert not (tmp_path / "models" / str(tool.id)).exists()


def test_deleting_a_model_removes_its_build(monkeypatch, logged_in, tmp_path):
    upload(logged_in, monkeypatch, BuildingRunner(built()), code=MODEL.replace("demo_box", "doomed"), name="doomed.py")
    tool = stored_tool("doomed")
    assert (tmp_path / "models" / str(tool.id)).exists()
    assert logged_in.delete(f"/manage/tool/delete/{tool.id}").status_code == 200
    assert stored_tool("doomed") is None and not (tmp_path / "models" / str(tool.id)).exists()


def test_optional_file_parameter_validates_with_none_and_runs_with_the_upload(monkeypatch, logged_in, tmp_path):
    import json

    runner = BuildingRunner(built())
    code = "# tag\n\nfrom pathlib import Path\nimport cadquery as cq\n\n\ndef relief(image: Path = None, size: float = 40) -> cq.Workplane:\n    return cq.Workplane().box(size, size, 2)\n"
    r = upload(logged_in, monkeypatch, runner, code=code, name="relief.py")
    assert r.status_code == 200, r.text
    # the validation build passed no values: the model's own defaults (image=None, size=40) built the demo
    assert runner.args == {}
    with db.Session(db.engine) as session:
        tool_id = session.exec(db.select(db.Tool).where(db.Tool.name == "relief")).first().id
    # a run with a file: it is saved under the run directory's inputs/<argument>/ and passed as a path
    r = logged_in.post(f"/tool/{tool_id}", files={"image": ("photo.png", b"png-bytes", "image/png")}, data={"size": "30"})
    assert r.status_code == 200, r.text
    run_dir = runner.calls[-1][1]
    saved = run_dir / "inputs" / "image" / "photo.png"
    assert runner.args["image"] == {"__path__": str(saved)} and runner.saved["inputs/image/photo.png"] == b"png-bytes"
    assert runner.args["size"] == 30.0


def test_the_default_build_is_served_and_shown(monkeypatch, logged_in, tmp_path):
    upload(logged_in, monkeypatch, BuildingRunner(built(size_mm=[10, 10, 10])), code=MODEL.replace("demo_box", "shown_box"),
           name="shown_box.py")
    tool_id = stored_tool("shown_box").id
    # the thumbnail and the default files are served from what the validation run produced
    preview = logged_in.get(f"/tool/{tool_id}/preview.svg")
    assert preview.headers["content-type"].startswith("image/svg+xml") and preview.headers["cache-control"] == "no-cache"
    # a browser revalidates with the ETag and gets a 304 while the thumbnail is unchanged
    assert logged_in.get(f"/tool/{tool_id}/preview.svg", headers={"If-None-Match": preview.headers["etag"]}).status_code == 304
    r = logged_in.get(f"/tool/{tool_id}/model.stl")
    assert r.status_code == 200 and r.text == "<model.stl>"
    assert logged_in.get(f"/tool/{tool_id}/model.step").text == "<model.step>"
    page = logged_in.get(f"/tool/{tool_id}").text
    assert f'<stl-viewer url="/tool/{tool_id}/model.stl">' in page and "10 &times; 10 &times; 10 mm" in page
    assert "[ regenerate ]" in page and f"cat shown_box.py" in page  # the code is still there, below the model


def test_a_private_models_files_are_not_served_to_others(monkeypatch, logged_in):
    upload(logged_in, monkeypatch, BuildingRunner(built()), code=MODEL.replace("demo_box", "secret_box"), name="secret_box.py")
    tool_id = stored_tool("secret_box").id  # uploads are private until published
    anonymous = TestClient(app)
    for path in (f"/tool/{tool_id}/preview.svg", f"/tool/{tool_id}/model.stl", f"/tool/{tool_id}/model.step"):
        assert anonymous.get(path).status_code == 404, path


def test_a_script_page_has_no_viewer_and_no_model_files(monkeypatch, logged_in):
    code = "def plain_page(n: int = 1) -> int:\n    return n\n"
    upload(logged_in, monkeypatch, BuildingRunner(), code=code, name="plain_page.py")
    tool_id = stored_tool("plain_page").id
    page = logged_in.get(f"/tool/{tool_id}").text
    assert "<stl-viewer" not in page and "[ regenerate ]" not in page and "[ run ]" in page
    assert logged_in.get(f"/tool/{tool_id}/preview.svg").status_code == 404
    assert logged_in.get(f"/tool/{tool_id}/model.stl").status_code == 404


def test_the_stored_thumbnail_cannot_run_script(monkeypatch, logged_in):
    # the run writes its own preview.svg: opened directly, a <script> in it must not run as the viewer
    upload(logged_in, monkeypatch, BuildingRunner(built()), code=MODEL.replace("demo_box", "inert_box"), name="inert_box.py")
    r = logged_in.get(f"/tool/{stored_tool('inert_box').id}/preview.svg")
    csp = r.headers["content-security-policy"]
    assert "sandbox" in csp and "default-src 'none'" in csp and "script-src" not in csp
    assert r.headers["x-content-type-options"] == "nosniff"


class GarbledPreviewRunner(BuildingRunner):
    """A build whose STL is new but whose thumbnail is not text."""

    async def run(self, tool, run_dir, on_line=None, runtime_args=()):
        result = await super().run(tool, run_dir, on_line, runtime_args)
        if not runtime_args and isinstance(result.results, dict):
            Path(result.results["stl"]).write_text("<new.stl>")
            Path(result.results["preview"]).write_bytes(b"\xff\xfe<svg>")
        return result


def test_a_build_whose_thumbnail_is_not_text_stores_nothing(monkeypatch, logged_in, tmp_path):
    r = upload(logged_in, monkeypatch, GarbledPreviewRunner(built()), code=MODEL.replace("demo_box", "garbled_box"),
               name="garbled_box.py")
    assert r.status_code == 400 and "preview.svg is not text" in r.json()["detail"]
    assert stored_tool("garbled_box") is None
    assert list((tmp_path / "models").glob("*/model.stl")) == []


def test_a_garbled_rebuild_keeps_the_previous_build(monkeypatch, logged_in, tmp_path):
    r = upload(logged_in, monkeypatch, BuildingRunner(built()), code=MODEL.replace("demo_box", "rebuilt_box"), name="rebuilt_box.py")
    assert r.status_code == 200, r.text
    tool = stored_tool("rebuilt_box")
    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=GarbledPreviewRunner(built())))
    code = MODEL.replace("demo_box", "rebuilt_box").replace("size, size, size", "size, size, 1")
    r = logged_in.post(f"/manage/tool/update/{tool.id}", files={"file": ("rebuilt_box.py", code.encode(), "text/x-python")})
    assert r.status_code == 400
    assert (tmp_path / "models" / str(tool.id) / "model.stl").read_text() == "<model.stl>"
    assert stored_tool("rebuilt_box").preview_svg == "<svg>preview</svg>" and stored_tool("rebuilt_box").code == tool.code


def test_a_script_never_serves_model_files(monkeypatch, logged_in, tmp_path):
    upload(logged_in, monkeypatch, BuildingRunner(), code="def stale(n: int = 1) -> int:\n    return n\n", name="stale.py")
    tool_id = stored_tool("stale").id
    left_over = tmp_path / "models" / str(tool_id)
    left_over.mkdir(parents=True)
    (left_over / "model.stl").write_text("left over")
    assert logged_in.get(f"/tool/{tool_id}/model.stl").status_code == 404
