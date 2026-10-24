"""pytools-admin apply-manifest: sets the owner's stored tools' tags and categories from a manifest; a dry
run by default, a JSON backup of the previous values before anything is saved."""

import json

from app import admin_cli, metadata

OWNER = 49600918
MANIFEST = {
    "box": {"tags": ["box", "lid"], "categories": ["home/storage"]},
    "hook": {"tags": ["hook"], "categories": ["home/wall", "workshop/tool-storage"]},
    "gone": {"tags": ["x"], "categories": ["misc"]},
}


def seed(make):
    return {"box": make("box", user_id=OWNER), "hook": make("hook", user_id=OWNER), "other": make("box", user_id=5)}


def test_dry_run_reports_and_saves_nothing(session_with_tools, tmp_path):
    session, make = session_with_tools
    ids = seed(make)
    code, lines = admin_cli.apply_manifest(session, MANIFEST, OWNER, apply=False, backup_dir=tmp_path)
    assert code == 0
    assert any(line.startswith("box:") and "home/storage" in line for line in lines)
    assert any("not stored: gone" in line for line in lines)
    assert metadata.load_all(session, [ids["box"]])[ids["box"]] == {"tags": [], "categories": ["misc"], "description": ""}
    assert list(tmp_path.iterdir()) == []


def test_apply_saves_and_backs_up(session_with_tools, tmp_path):
    session, make = session_with_tools
    ids = seed(make)
    metadata.apply(session, ids["box"], {"tags.present": ["1"], "tags": ["old"]})
    session.commit()
    code, _ = admin_cli.apply_manifest(session, MANIFEST, OWNER, apply=True, backup_dir=tmp_path)
    assert code == 0
    loaded = metadata.load_all(session, [ids["box"], ids["hook"], ids["other"]])
    assert loaded[ids["box"]] == {"tags": ["box", "lid"], "categories": ["home/storage"], "description": ""}
    assert loaded[ids["hook"]]["categories"] == ["home/wall", "workshop/tool-storage"]
    assert loaded[ids["other"]] == {"tags": [], "categories": ["misc"], "description": ""}  # another user's tool is never touched
    [backup] = list(tmp_path.iterdir())
    previous = json.loads(backup.read_text())
    assert previous[str(ids["box"])] == {"name": "box", "tags": ["old"], "categories": ["misc"], "description": ""}
    # running it again changes nothing and writes no second backup
    code, lines = admin_cli.apply_manifest(session, MANIFEST, OWNER, apply=True, backup_dir=tmp_path)
    assert code == 0 and len(list(tmp_path.iterdir())) == 1 and not any(line.startswith("box:") for line in lines)


def test_duplicate_owner_names_stop_everything(session_with_tools, tmp_path):
    session, make = session_with_tools
    seed(make)
    make("hook", user_id=OWNER)  # a second "hook" owned by the owner
    code, lines = admin_cli.apply_manifest(session, MANIFEST, OWNER, apply=True, backup_dir=tmp_path)
    assert code == 1 and any("hook" in line and "more than one" in line for line in lines)
    assert list(tmp_path.iterdir()) == []


def test_invalid_manifest_stops_before_any_change(session_with_tools, tmp_path):
    session, make = session_with_tools
    ids = seed(make)
    bad = {**MANIFEST, "hook": {"tags": ["hook"], "categories": ["home/nope"]}}
    code, lines = admin_cli.apply_manifest(session, bad, OWNER, apply=True, backup_dir=tmp_path)
    assert code == 1 and any("hook" in line and "unknown category" in line for line in lines)
    assert metadata.load_all(session, [ids["box"]])[ids["box"]]["tags"] == []


def test_manifest_descriptions_are_optional_and_left_alone_when_absent(session_with_tools, tmp_path):
    session, make = session_with_tools
    ids = seed(make)
    metadata.apply(session, ids["hook"], {"description.present": ["1"], "description": ["written on the site"]})
    session.commit()
    manifest = {**MANIFEST, "box": {**MANIFEST["box"], "description": "From the manifest."}}
    code, _ = admin_cli.apply_manifest(session, manifest, OWNER, apply=True, backup_dir=tmp_path)
    loaded = metadata.load_all(session, [ids["box"], ids["hook"]])
    assert code == 0 and loaded[ids["box"]]["description"] == "From the manifest."
    assert loaded[ids["hook"]]["description"] == "written on the site"  # no description in its entry: kept


def test_an_entry_names_its_file_and_the_file_is_not_metadata(session_with_tools, tmp_path):
    session, make = session_with_tools
    ids = seed(make)
    manifest = {"box": {"file": "box.py", "tags": ["box"], "categories": ["home/storage"]}}
    code, _ = admin_cli.apply_manifest(session, manifest, OWNER, apply=True, backup_dir=tmp_path)
    assert code == 0 and metadata.load_all(session, [ids["box"]])[ids["box"]]["tags"] == ["box"]


# --- creating the repo's models that the site does not have yet ------------------------------------------------

MODELS = {
    "new_box": {"file": "models/new_box.py", "tags": ["box"], "categories": ["home/storage"], "description": "A box."},
    "new_hook": {"file": "models/new_hook.py", "tags": ["hook"], "categories": ["home/wall"]},
    "a_script": {"file": "converters/a_script.py", "tags": ["x"], "categories": ["text/formatting"]},
}


def repo(tmp_path):
    (tmp_path / "models").mkdir(parents=True)
    for name in ("new_box", "new_hook"):
        (tmp_path / "models" / f"{name}.py").write_text(f"def {name}() -> int:\n    return 1\n")
    return tmp_path


class FakeSite:
    """Stands in for the running app's upload route: stores the tool (as the route would) or fails."""

    def __init__(self, session, fail=()):
        self.session, self.fail, self.posts = session, set(fail), []

    def __call__(self, filename, code, form):
        from app.models.tools import Tool

        self.posts.append((filename, code, form))
        name = filename.removesuffix(".py")
        if name in self.fail:
            return 400, "Model Build Failed: boom"
        self.session.add(Tool(name=name, code=code.decode(), user_id=OWNER))
        self.session.commit()
        return 200, ""


def test_a_dry_run_lists_the_models_to_create_and_creates_nothing(session_with_tools, tmp_path):
    session, _ = session_with_tools
    site = FakeSite(session)
    lines = admin_cli.create_missing(session, MODELS, OWNER, False, repo(tmp_path), site)
    assert "create new_box" in lines and "create new_hook" in lines and site.posts == []
    assert not any("a_script" in line for line in lines)  # only the repo's models are ever created


def test_creating_posts_the_file_and_its_metadata_then_publishes(session_with_tools, tmp_path):
    from app.models.tools import Tool

    session, _ = session_with_tools
    site = FakeSite(session)
    lines = admin_cli.create_missing(session, MODELS, OWNER, True, repo(tmp_path), site)
    assert [p[0] for p in site.posts] == ["new_box.py", "new_hook.py"]
    filename, code, form = site.posts[0]
    assert code == b"def new_box() -> int:\n    return 1\n"
    assert form["tags"] == ["box"] and form["categories"] == ["home/storage"] and form["description"] == ["A box."]
    stored = session.exec(admin_cli.select(Tool).where(Tool.name == "new_box")).first()
    assert stored.public and "created new_box" in lines
    # a second run finds them stored and creates nothing
    assert admin_cli.create_missing(session, MODELS, OWNER, True, repo(tmp_path / "again"), FakeSite(session)) == []


def test_a_failed_build_is_reported_and_the_rest_still_created(session_with_tools, tmp_path):
    session, _ = session_with_tools
    lines = admin_cli.create_missing(session, MODELS, OWNER, True, repo(tmp_path), FakeSite(session, fail={"new_box"}))
    assert "FAILED new_box: Model Build Failed: boom" in lines and "created new_hook" in lines


def test_http_post_uploads_as_the_owner_through_the_real_route(monkeypatch):
    """The request http_post builds (multipart body, signed session cookie) replayed against the app itself."""
    import urllib.request

    from fastapi.testclient import TestClient
    from sandboxcore.host import Sandbox

    from app.app import app
    from app.models import tools as db
    from app.routes import tools as tools_routes
    from tests.test_tool_routes import StubRunner

    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=StubRunner()))
    client = TestClient(app)

    def urlopen(request, timeout=None):
        r = client.post("/manage/tool/upload", content=request.data, headers=dict(request.header_items()))
        assert r.status_code == 200, r.text
        return type("R", (), {"status": r.status_code, "__enter__": lambda self: self, "__exit__": lambda *a: None})()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    post = admin_cli.http_post("http://app", OWNER)
    form = admin_cli._form({"tags": ["posted"], "categories": ["home/storage"], "description": "Sent."})
    assert post("posted_tool.py", b"def posted_tool() -> int:\n    return 1\n", form) == (200, "")
    with db.Session(db.engine) as session:
        tool = session.exec(db.select(db.Tool).where(db.Tool.name == "posted_tool")).first()
        assert tool is not None and tool.user_id == OWNER
        assert metadata.load_all(session, [tool.id])[tool.id] == {
            "tags": ["posted"], "categories": ["home/storage"], "description": "Sent."}
