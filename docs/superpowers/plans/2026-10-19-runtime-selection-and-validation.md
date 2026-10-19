# Runtime Selection and Tool Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Uploaders pick one of the runtimes defined by `containers/runtimes/<name>.Containerfile`, supply default inputs and sample files, and a tool becomes public only after a validation run succeeds in that runtime.

**Architecture:** The runtime list is discovered from a folder of Containerfiles shipped in the app image; `PodmanRunner` keeps per-runtime image/availability state and takes the runtime per run. `tool` gains `runtime`, `defaults`, `validated` (+ reserved `source`/`source_ref`) via an idempotent startup migration. The user page's tool rows get a runtime dropdown, a dependencies viewer, and a configure/validate panel that runs the tool through the normal runner.

**Tech Stack:** FastAPI/Starlette 1.x, SQLModel/SQLite, htmx + hyperscript, Tailwind v4 (rebuild `output.css` with the CLI on the server), podman 5 nested runner, GitHub Actions matrix, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-10-19-runtime-selection-and-validation-design.md`

## Global Constraints

- Runtime names are file names: `containers/runtimes/<name>.Containerfile`; images are `SANDBOX_IMAGE_PREFIX` (default `docker.io/raubcamaioni/pywebtools-sandbox-`) + name + `:latest`. Initial runtimes: `python`, `deps`, `cadquery`.
- Every runtime Containerfile: comment header, `FROM python:3.12-slim-bookworm`, user `app` uid 1001, sandbox package in `/venvs/sandbox`, one explicit `pip install` line, entrypoint `/venvs/sandbox/bin/sandbox`.
- New `tool` columns and defaults: `runtime TEXT DEFAULT 'deps'`, `defaults JSON DEFAULT '{}'`, `validated BOOLEAN DEFAULT 0`, `source TEXT DEFAULT 'upload'`, `source_ref TEXT NULL`. Migration marks pre-existing rows `validated=1`.
- Visibility: visitors see a tool only when `public and validated`; owners always; `?public=true` refused with `400 Validate the tool first` while unvalidated.
- Sample files: `/data/tools/<id>/samples/<file name>`; the app's data root is `Path(ENVIRONMENT.DATABASE).parent`.
- Messages verbatim: `Validate the tool first`, `runtime "<name>" no longer exists`, `Sandbox unavailable`, `validated`, `not validated`.
- All runtimes share the limits in `SandboxConfig`; `SANDBOX_IMAGE` (single image) is removed from the config.
- Tests: `cd server && python -m pytest -m "not integration"` must stay green after every task; integration tests run inside the app container with `SANDBOX_INTEGRATION=1`. CSS: rebuild with the Tailwind CLI whenever templates gain classes, commit `output.css`.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; push to `main` allowed; no push before Task 8 (CI must not build half-migrated images).

## Review Focus

1. A tool whose `runtime` names a file that no longer exists → owner sees `runtime "<name>" no longer exists`, visitors get `503 Sandbox unavailable`, no exception. Tests in Task 4 (`test_run_unknown_runtime_raises_unavailable`) and Task 7 (`test_configure_panel_shows_missing_runtime`).
2. A sample file name containing path separators or `..` must be stored under the tool's samples directory only. Test in Task 6 (`test_validate_rejects_sample_names_with_paths`).
3. Validation of a tool with a `Path` argument but no sample uploaded and none stored → `400` naming the argument, not a crash. Test in Task 6 (`test_validate_requires_a_sample_for_path_arguments`).
4. Migration on the production-shaped database (old columns only) must be idempotent across restarts and must not touch `validated` on second run. Test in Task 2 (`test_migration_is_idempotent`).
5. A visitor submitting the tool-page form without a file for a `Path` argument gets the stored sample; with a file, theirs wins. Test in Task 7 (`test_run_uses_stored_sample_when_no_file_submitted`, `test_run_prefers_submitted_file`).

---

### Task 1: Runtime discovery and config

**Files:**
- Create: `server/src/app/utility/runtimes.py`
- Modify: `server/src/app/utility/sandbox_config.py`
- Create: `containers/runtimes/python.Containerfile`, `containers/runtimes/deps.Containerfile`, `containers/runtimes/cadquery.Containerfile`
- Delete: `containers/Containerfile.sandbox`
- Modify: `sandbox/pyproject.toml` (dependencies → `[]`)
- Test: `server/tests/test_runtimes.py`, `server/tests/test_sandbox_config.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Runtime: name: str; containerfile: Path`; `discover_runtimes(folder: Path) -> list[Runtime]` (sorted by name, `*.Containerfile` only, empty list when the folder is missing); `Runtime.image(prefix: str) -> str` = `f"{prefix}{name}:latest"`.
- Produces: `SandboxConfig` loses `image`; gains `runtimes_dir: Path` (`SANDBOX_RUNTIMES_DIR`, default `/runtimes`) and `image_prefix: str` (`SANDBOX_IMAGE_PREFIX`, default `docker.io/raubcamaioni/pywebtools-sandbox-`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runtimes.py
from pathlib import Path
from app.utility.runtimes import Runtime, discover_runtimes

def test_discovers_sorted_names_from_containerfiles(tmp_path):
    for n in ("deps", "cadquery", "python"): (tmp_path / f"{n}.Containerfile").write_text("FROM x")
    (tmp_path / "README.md").write_text("ignored")
    assert [r.name for r in discover_runtimes(tmp_path)] == ["cadquery", "deps", "python"]
    assert discover_runtimes(tmp_path)[0].containerfile == tmp_path / "cadquery.Containerfile"

def test_missing_folder_gives_no_runtimes(tmp_path):
    assert discover_runtimes(tmp_path / "nope") == []

def test_image_name_from_prefix():
    assert Runtime("deps", Path("x")).image("docker.io/acme/sb-") == "docker.io/acme/sb-deps:latest"

def test_repo_runtimes_folder_has_the_three_initial_runtimes():
    repo = Path(__file__).resolve().parents[2]
    assert [r.name for r in discover_runtimes(repo / "containers" / "runtimes")] == ["cadquery", "deps", "python"]
```
In `test_sandbox_config.py::test_defaults_from_empty_environment` add: `assert cfg.runtimes_dir == Path("/runtimes") and cfg.image_prefix == "docker.io/raubcamaioni/pywebtools-sandbox-"` and `assert not hasattr(cfg, "image")`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_runtimes.py tests/test_sandbox_config.py -v`
Expected: FAIL with `ModuleNotFoundError: app.utility.runtimes`

- [ ] **Step 3: Implement `runtimes.py`, the config fields, and the three Containerfiles**

Each Containerfile follows the Global Constraints template; `python` has no pip line beyond the sandbox package, `deps` installs `numpy scipy pandas opencv-python av pymupdf pydantic pyparsing`, `cadquery` installs the `deps` list plus `cadquery ezdxf`. Set `sandbox/pyproject.toml` `dependencies = []`. Remove `containers/Containerfile.sandbox`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_runtimes.py tests/test_sandbox_config.py -v`
Expected: all passed (the old `SANDBOX_IMAGE` assertions removed along with the field)

- [ ] **Step 5: Commit**

```bash
git add containers/runtimes sandbox/pyproject.toml server/src/app/utility/runtimes.py server/src/app/utility/sandbox_config.py server/tests/test_runtimes.py server/tests/test_sandbox_config.py
git rm containers/Containerfile.sandbox
git commit -m "Define sandbox runtimes as Containerfiles in containers/runtimes"
```

### Task 2: Tool columns and the startup migration

**Files:**
- Modify: `server/src/app/models/tools.py:43-57` (`Tool`), `:206-208` (`create_db_and_tables`)
- Test: `server/tests/test_migration.py`

**Interfaces:**
- Produces: `Tool.runtime: str = "deps"`, `Tool.defaults: dict = {}` (`Column(JSON)`), `Tool.validated: bool = False`, `Tool.source: str = "upload"`, `Tool.source_ref: Optional[str] = None`.
- Produces: `migrate_tool_table(engine) -> list[str]` (names of columns added), called by `create_db_and_tables()` after `create_all`. Adds missing columns with the Global Constraints defaults; when it adds `validated`, runs `UPDATE tool SET validated = 1`.

- [ ] **Step 1: Write the failing tests**

```python
import sqlite3
from sqlmodel import create_engine
from app.models.tools import migrate_tool_table

OLD = """create table tool (id integer primary key, name text, code text, arguments json, tags json,
usage integer default 0, public boolean default 0, annonymous boolean default 1, user_id integer)"""

def old_db(tmp_path):
    db = tmp_path / "old.db"
    c = sqlite3.connect(db); c.execute(OLD)
    c.execute("insert into tool (id, name, code, public) values (4, 'container_with_lid', 'def f(): pass', 1)")
    c.commit(); c.close()
    return db

def test_migration_adds_columns_and_grandfathers_existing_rows(tmp_path):
    db = old_db(tmp_path)
    added = migrate_tool_table(create_engine(f"sqlite:///{db}"))
    assert set(added) == {"runtime", "defaults", "validated", "source", "source_ref"}
    row = sqlite3.connect(db).execute("select runtime, defaults, validated, source, source_ref from tool where id=4").fetchone()
    assert row == ("deps", "{}", 1, "upload", None)

def test_migration_is_idempotent(tmp_path):
    db = old_db(tmp_path)
    engine = create_engine(f"sqlite:///{db}")
    migrate_tool_table(engine)
    sqlite3.connect(db).execute("update tool set validated = 0").connection.commit()
    assert migrate_tool_table(engine) == []
    assert sqlite3.connect(db).execute("select validated from tool where id=4").fetchone() == (0,)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_migration.py -v`
Expected: FAIL with `ImportError: cannot import name 'migrate_tool_table'`

- [ ] **Step 3: Implement the fields and `migrate_tool_table`**

Use `PRAGMA table_info(tool)` to find existing columns; `ALTER TABLE tool ADD COLUMN <name> <type> DEFAULT <default>` for each missing one, in a single transaction; return the added names.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_migration.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/models/tools.py server/tests/test_migration.py
git commit -m "Add runtime, defaults, validated and source columns to tools with a startup migration"
```

### Task 3: Per-runtime runner state

**Files:**
- Modify: `server/src/app/utility/podman_runner.py`
- Test: `server/tests/test_podman_startup.py`, `server/tests/test_podman_run.py`

**Interfaces:**
- Produces: `PodmanRunner.__init__(self, config, runtimes: list[Runtime], exec=None, sleep=asyncio.sleep)`; `runtime_names: list[str]`; `status() -> dict[str, str]` (name → `"ready"` | `"starting"` | reason); `available_for(name) -> bool`; `unavailable_reason_for(name) -> str | None`; `available` = any runtime ready; `run(tool, run_dir, runtime: str)` raising `SandboxUnavailable(f'runtime "{runtime}" no longer exists')` for unknown names and `SandboxUnavailable(reason)` for an unavailable one.
- Startup: for each runtime, `pull`/`image exists`/self-test exactly as today, per image; `mark_unavailable(name, reason)` / `mark_available(name)`; retry loop covers runtimes not ready; refresh pulls every image. `command()` takes the image: `command(name, tool, run_dir, image)`.
- Consumes: `Runtime` (Task 1).

- [ ] **Step 1: Write the failing tests** (replace the single-image tests)

```python
# test_podman_startup.py additions; RT = [Runtime("python", Path("p")), Runtime("deps", Path("d"))]
async def test_start_pulls_and_self_tests_every_runtime():
    fake = ScriptedPodman(run_responses=[(137,"",""),(255,"","")]*2)
    runner = PodmanRunner(cfg(), RT, exec=fake, sleep=no_sleep); await runner.start(); await runner.stop()
    pulled = [c[2] for c in fake.calls if c[1] == "pull"]
    assert pulled == [cfg().image_prefix + "python:latest", cfg().image_prefix + "deps:latest"]
    assert runner.status() == {"python": "ready", "deps": "ready"} and runner.available

async def test_one_bad_runtime_leaves_the_other_ready():
    fake = ScriptedPodman(run_responses=[(137,"",""),(255,"",""),(0,"",""),(255,"","")])
    runner = PodmanRunner(cfg(), RT, exec=fake, sleep=no_sleep); await runner.start(); await runner.stop()
    assert runner.available_for("python") and not runner.available_for("deps")
    assert runner.status()["deps"] == "memory limit not enforced" and runner.available

async def test_new_runner_reports_starting_for_every_runtime():
    runner = PodmanRunner(cfg(), RT, exec=FakePodman(), sleep=no_sleep)
    assert runner.status() == {"python": "starting", "deps": "starting"} and not runner.available
```
```python
# test_podman_run.py additions (ready_runner marks every runtime available)
async def test_run_uses_the_runtimes_image(tmp_path):
    fake = FakePodman({"inspect": (0, "0 false", "")})
    await ready_runner(cfg(), fake).run(tmp_path / "t.py", tmp_path, "python")
    assert cfg().image_prefix + "python:latest" in fake.calls[0]

async def test_run_unknown_runtime_raises_unavailable(tmp_path):
    with pytest.raises(SandboxUnavailable, match='runtime "go" no longer exists'):
        await ready_runner(cfg(), FakePodman()).run(tmp_path / "t.py", tmp_path, "go")

async def test_run_unavailable_runtime_raises_its_reason(tmp_path):
    runner = ready_runner(cfg(), FakePodman()); runner.mark_unavailable("deps", "memory limit not enforced")
    with pytest.raises(SandboxUnavailable, match="memory limit not enforced"):
        await runner.run(tmp_path / "t.py", tmp_path, "deps")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_podman_startup.py tests/test_podman_run.py -v`
Expected: FAIL with `TypeError` (constructor signature) and `AttributeError: status`

- [ ] **Step 3: Implement per-runtime state**

Keep one `asyncio.Semaphore` for all runtimes (capacity is a host property). Self-test commands use the runtime's image. Existing tests that passed a single image are updated to the new constructor via `ready_runner`.

- [ ] **Step 4: Run the unit suite**

Run: `cd server && python -m pytest -m "not integration" -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/podman_runner.py server/tests/test_podman_startup.py server/tests/test_podman_run.py
git commit -m "Track sandbox availability per runtime and run tools in their runtime's image"
```

### Task 4: Wire runtimes into the app: healthz, run route, visibility, /runtimes

**Files:**
- Modify: `server/src/app/routes/tools.py` (`runner` construction, `/healthz`, `run_isolated`, `entrypoint_page`, `get_tools` filtering), `server/src/app/models/tools.py` (`get_tools_by_index`, `get_tools_by_tags`: `only_public` → `public and validated`)
- Test: `server/tests/test_tool_routes.py`

**Interfaces:**
- Produces: `runner = PodmanRunner(ENVIRONMENT.sandbox, discover_runtimes(ENVIRONMENT.sandbox.runtimes_dir))`; `GET /healthz` → `200 {"sandbox": "ready", "runtimes": {...}}` when all ready, `503 {"sandbox": "degraded"|"unavailable", "runtimes": {...}}` otherwise (`degraded` = some ready).
- Produces: `GET /runtimes/{name}` → `text/plain` body of the Containerfile, 404 for unknown names. `GET /runtimes` → JSON list of names.
- Produces: `run_isolated` passes `tool.runtime`; visitors (non-owners) get 404 for tools that are not `public and validated`; `SandboxUnavailable` → `503 Sandbox unavailable`.

- [ ] **Step 1: Write the failing tests**

```python
def test_healthz_reports_each_runtime(monkeypatch):
    stub = StubRunner(); stub.status_map = {"python": "ready", "deps": "starting"}
    r = client(monkeypatch, stub).get("/healthz")
    assert r.status_code == 503 and r.json() == {"sandbox": "degraded", "runtimes": {"python": "ready", "deps": "starting"}}

def test_runtimes_endpoints(monkeypatch, tmp_path):
    (tmp_path / "deps.Containerfile").write_text("FROM python:3.12-slim-bookworm\n# deps\n")
    monkeypatch.setattr(tools_routes, "RUNTIMES", discover_runtimes(tmp_path))
    c = client(monkeypatch, StubRunner())
    assert c.get("/runtimes").json() == ["deps"]
    assert c.get("/runtimes/deps").text.startswith("FROM python") and c.get("/runtimes/go").status_code == 404

def test_visitor_cannot_see_unvalidated_tool(monkeypatch, public_tool):
    monkeypatch.setattr(db, "get_tool_by_id", lambda s, id: db.Tool(id=8, name="t", code="", arguments={}, public=True, validated=False, tags=[], user_id=1))
    c = client(monkeypatch, StubRunner())
    assert c.get("/tool/8").status_code == 404 and c.post("/tool/8").status_code == 404

def test_run_passes_the_tools_runtime(monkeypatch, public_tool):
    stub = StubRunner(RunResult(Outcome.OK, results=1))
    client(monkeypatch, stub).post("/tool/8")
    assert stub.calls[0][2] == "deps"   # StubRunner.run records (tool, run_dir, runtime)
```
`StubRunner` gains `status_map` (returned by `status()`), `available_for(name)` (= `available`), and `run(self, tool, run_dir, runtime)`. The `public_tool` fixture's Tool gets `validated=True`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_tool_routes.py -v`
Expected: FAIL (`/runtimes` 404, healthz shape, missing runtime argument)

- [ ] **Step 3: Implement**

`RUNTIMES = discover_runtimes(ENVIRONMENT.sandbox.runtimes_dir)` module global in `routes/tools.py`; the Containerfile text is read on each request (files are small, folder is read-only). Visibility check becomes a helper `_visible_to(request, tool) -> bool` used by `entrypoint_page`, `run_isolated`, `download_tool`.

- [ ] **Step 4: Run the unit suite**

Run: `cd server && python -m pytest -m "not integration" -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/routes/tools.py server/src/app/models/tools.py server/tests/test_tool_routes.py
git commit -m "Expose runtimes, report health per runtime, and hide unvalidated tools"
```

### Task 5: Runtime dropdown and validated badge on the profile rows

**Files:**
- Modify: `server/src/app/utility/render.py:154-170` (`list_item_user`), `server/src/app/webapp/templates/components/update_tool_item.html`, `server/src/app/routes/upload.py` (`tool_set_public` refusal; new `POST /manage/tool/runtime/{id}`), `server/src/app/webapp/static/input.css` (if new classes)
- Test: `server/tests/test_upload_routes.py` (new), `server/tests/test_render.py` (new)

**Interfaces:**
- Produces: `render.list_item_user(root_path, tools, runtimes: list[str]) -> str`; each row shows a `<select name="runtime">` with the runtime names (current one selected) that posts `POST /manage/tool/runtime/{id}` (form field `runtime`) via `hx-post`/`hx-trigger="change"`, a `[ dependencies ]` link that loads `GET /runtimes/{name}` into a `<pre>` under the row (`hx-get`, toggled), and a badge `validated` / `not validated`.
- Produces: `POST /manage/tool/runtime/{id}` (owner only): stores `runtime` if it is a known name (`400 Unknown runtime` otherwise), sets `validated=false`, returns 200.
- Produces: `POST /manage/tool/settings/{id}?public=true` → `400 Validate the tool first` when not validated.

- [ ] **Step 1: Write the failing tests**

```python
# test_render.py
def test_user_row_has_runtime_select_and_badge():
    tool = db.Tool(id=4, name="container_with_lid", code="", arguments={}, tags=[], runtime="cadquery", validated=True, public=True)
    html = render.list_item_user("", [tool], ["cadquery", "deps", "python"])
    assert '<option value="cadquery" selected>' in html and '<option value="python">' in html
    assert ">validated<" in html and 'hx-get="/runtimes/cadquery"' in html

# test_upload_routes.py (session helper: set request.session["user"] via a login-stub route or by monkeypatching _session_user)
def test_set_public_refused_until_validated(owner_client, unvalidated_tool):
    r = owner_client.post("/manage/tool/settings/11?public=true")
    assert r.status_code == 400 and r.json()["detail"] == "Validate the tool first"

def test_change_runtime_resets_validation(owner_client, validated_tool):
    r = owner_client.post("/manage/tool/runtime/4", data={"runtime": "python"})
    assert r.status_code == 200 and validated_tool.runtime == "python" and validated_tool.validated is False
    assert owner_client.post("/manage/tool/runtime/4", data={"runtime": "go"}).status_code == 400
```
The `owner_client` fixture logs a user in by posting to a test-only route added in `conftest.py` (`app.add_api_route("/_test/login/{id}", ...)` that sets `request.session["user"]`), and the tool fixtures monkeypatch `tools.get_tool` / `get_tool_by_id` to return in-memory `Tool` objects with `user_id` matching.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_render.py tests/test_upload_routes.py -v`
Expected: FAIL with `TypeError` (`list_item_user` arity) and 404 on `/manage/tool/runtime/4`

- [ ] **Step 3: Implement**

Dropdown markup follows the theme (bordered select, `[ dependencies ]` link with hover invert, badge in `text-dim` or `text-paper`). `render.list_item_user` reads `tool.runtime` and `tool.validated`. Rebuild `output.css` if new utilities are used.

- [ ] **Step 4: Run the unit suite**

Run: `cd server && python -m pytest -m "not integration" -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/render.py server/src/app/webapp server/src/app/routes/upload.py server/tests/test_render.py server/tests/test_upload_routes.py server/tests/conftest.py
git commit -m "Runtime dropdown, dependencies viewer and validated badge on the profile rows"
```

### Task 6: Validate route with defaults and sample files

**Files:**
- Create: `server/src/app/utility/samples.py`
- Modify: `server/src/app/routes/upload.py` (`POST /manage/tool/validate/{id}`, `tool_upload_post` sets defaults from the signature, `tool_upload_post` update path re-validates)
- Test: `server/tests/test_samples.py`, `server/tests/test_upload_routes.py`

**Interfaces:**
- Produces: `samples.sample_dir(data_root: Path, tool_id: int) -> Path` (`<data_root>/tools/<id>/samples`); `samples.store(data_root, tool_id, filename, content: bytes) -> Path` raising `ValueError` when `Path(filename).name != filename` or the name is empty; `samples.copy_into(data_root, tool_id, filename, run_dir) -> Path`.
- Produces: `POST /manage/tool/validate/{id}` (owner only, multipart): fields are the argument names (file fields for `Path` arguments), plus `runtime`. For each `Path` argument: uploaded file → stored as the sample and recorded in `defaults` as its name; no upload and an existing sample → kept; neither → `400 Missing sample for <name>`. Other arguments → stored as strings in `defaults`. Then runs the tool via `runner.run(tool_file, run_dir, runtime)` with `args.json` built exactly as `run_isolated` does, sets `validated` from the outcome, and returns the rendered result (HTMX) or JSON `{"validated": bool, "detail": message}`.
- Produces: `tool_upload_post` update path: after replacing code, sets `validated=False` and runs the same validation with stored defaults, returning its result.
- Consumes: `PodmanRunner.run(tool, run_dir, runtime)` (Task 3), visibility helpers (Task 4).

- [ ] **Step 1: Write the failing tests**

```python
# test_samples.py
def test_store_and_copy_sample(tmp_path):
    p = samples.store(tmp_path, 4, "in.txt", b"HeLLo")
    assert p == tmp_path / "tools" / "4" / "samples" / "in.txt" and p.read_bytes() == b"HeLLo"
    run_dir = tmp_path / "run"; run_dir.mkdir()
    assert samples.copy_into(tmp_path, 4, "in.txt", run_dir) == run_dir / "in.txt"

@pytest.mark.parametrize("bad", ["../x.txt", "a/b.txt", "", "C:\\\\x.txt"])
def test_validate_rejects_sample_names_with_paths(tmp_path, bad):
    with pytest.raises(ValueError):
        samples.store(tmp_path, 4, bad, b"x")

# test_upload_routes.py
def test_validate_success_marks_validated_and_stores_defaults(owner_client, unvalidated_tool, stub_runner):
    stub_runner.result = RunResult(Outcome.OK, results="0x68 0x69")
    r = owner_client.post("/manage/tool/validate/11", data={"runtime": "python", "input": "hi", "output": "hexadecimal"})
    assert r.status_code == 200 and unvalidated_tool.validated is True
    assert unvalidated_tool.defaults == {"input": "hi", "output": "hexadecimal"} and unvalidated_tool.runtime == "python"
    assert stub_runner.calls[0][2] == "python"

def test_validate_failure_keeps_tool_unvalidated(owner_client, unvalidated_tool, stub_runner):
    stub_runner.result = RunResult(Outcome.TIMEOUT, message="Tool exceeded the 30 second limit")
    r = owner_client.post("/manage/tool/validate/11", data={"runtime": "deps"})
    assert r.status_code == 200 and "exceeded" in r.text and unvalidated_tool.validated is False

def test_validate_requires_a_sample_for_path_arguments(owner_client, path_tool):
    r = owner_client.post("/manage/tool/validate/12", data={"runtime": "deps"})
    assert r.status_code == 400 and r.json()["detail"] == "Missing sample for image_file"

def test_validate_stores_uploaded_sample(owner_client, path_tool, stub_runner, tmp_path):
    stub_runner.result = RunResult(Outcome.OK, results="ok")
    r = owner_client.post("/manage/tool/validate/12", data={"runtime": "deps"}, files={"image_file": ("pixel.png", b"\x89PNG", "image/png")})
    assert r.status_code == 200 and path_tool.defaults == {"image_file": "pixel.png"}
    assert (tmp_path / "tools" / "12" / "samples" / "pixel.png").read_bytes() == b"\x89PNG"
```
(`path_tool` has `arguments={"image_file": ("Path", None)}`; the data root is `tmp_path` via `monkeypatch.setattr(upload_routes, "DATA_ROOT", tmp_path)`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_samples.py tests/test_upload_routes.py -v`
Expected: FAIL with `ModuleNotFoundError: app.utility.samples` and 404 on the validate route

- [ ] **Step 3: Implement**

Factor the `args.json` construction out of `run_isolated` into `utility/run_inputs.py: build_run_inputs(tool, run_dir, form, data_root) -> dict` used by both routes (Task 7 reuses it for sample fallback). `DATA_ROOT = Path(ENVIRONMENT.DATABASE).parent` in `routes/upload.py`.

- [ ] **Step 4: Run the unit suite**

Run: `cd server && python -m pytest -m "not integration" -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/samples.py server/src/app/utility/run_inputs.py server/src/app/routes/upload.py server/src/app/routes/tools.py server/tests/test_samples.py server/tests/test_upload_routes.py
git commit -m "Validate tools with stored defaults and sample files before they can go public"
```

### Task 7: Configure panel and tool-page defaults

**Files:**
- Create: `server/src/app/webapp/templates/components/configure_tool.html`
- Modify: `server/src/app/webapp/templates/components/update_tool_item.html` (`[ validate ]` loads the panel via `hx-get="/manage/tool/configure/{id}"`), `server/src/app/routes/upload.py` (`GET /manage/tool/configure/{id}`), `server/src/app/utility/render.py` (`args_to_form(arguments, defaults=None, samples=None)`), `server/src/app/webapp/templates/components/form_type.html` (sample name hint for file inputs), `server/src/app/routes/tools.py` (`entrypoint_page` passes defaults/samples; `run_isolated` uses `build_run_inputs` with sample fallback)
- Test: `server/tests/test_upload_routes.py`, `server/tests/test_tool_routes.py`, `server/tests/test_render.py`

**Interfaces:**
- Produces: `GET /manage/tool/configure/{id}` (owner only) → HTML panel: runtime select (current), `[ dependencies ]` viewer, the argument form pre-filled from `defaults` (file inputs show `sample: <name>`), `[ validate ]` posting to the Task 6 route with `hx-target` on a result area inside the panel; when `tool.runtime` is not a known name the panel shows `runtime "<name>" no longer exists` and selects nothing.
- Produces: `render.args_to_form(arguments, defaults=None, samples=None)`: `defaults[name]` overrides the signature default; `samples[name]` renders the hint and drops `required` from that file input.
- Produces: `run_isolated` fallback: a `Path` argument with no uploaded file and a stored sample copies the sample into the run dir.

- [ ] **Step 1: Write the failing tests**

```python
def test_configure_panel_prefills_defaults_and_sample(owner_client, path_tool):
    path_tool.defaults = {"image_file": "pixel.png"}; path_tool.runtime = "deps"
    html = owner_client.get("/manage/tool/configure/12").text
    assert 'sample: pixel.png' in html and '<option value="deps" selected>' in html and "[ validate ]" in html

def test_configure_panel_shows_missing_runtime(owner_client, path_tool):
    path_tool.runtime = "go"
    assert 'runtime "go" no longer exists' in owner_client.get("/manage/tool/configure/12").text

def test_run_uses_stored_sample_when_no_file_submitted(monkeypatch, public_path_tool, stub_runner, tmp_path):
    samples.store(tmp_path, 12, "pixel.png", b"\x89PNG")
    client(monkeypatch, stub_runner).post("/tool/12")
    tool, run_dir, runtime = stub_runner.calls[0]
    assert (run_dir / "pixel.png").read_bytes() == b"\x89PNG"
    assert serializer.load(open(run_dir / "args.json"))["image_file"] == run_dir / "pixel.png"

def test_run_prefers_submitted_file(monkeypatch, public_path_tool, stub_runner, tmp_path):
    samples.store(tmp_path, 12, "pixel.png", b"\x89PNG")
    client(monkeypatch, stub_runner).post("/tool/12", files={"image_file": ("mine.png", b"MINE", "image/png")})
    _, run_dir, _ = stub_runner.calls[0]
    assert (run_dir / "mine.png").read_bytes() == b"MINE" and not (run_dir / "pixel.png").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_upload_routes.py tests/test_tool_routes.py tests/test_render.py -v`
Expected: FAIL (404 on the configure route; sample not copied)

- [ ] **Step 3: Implement**, rebuild `output.css` for new classes, keep the terminal style (panel opens under the row; `$ validate name.py --runtime deps` as the panel heading).

- [ ] **Step 4: Run the unit suite**

Run: `cd server && python -m pytest -m "not integration" -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app server/tests
git commit -m "Configure panel: runtime, defaults and samples; tool page uses stored defaults"
```

### Task 8: App image carries the runtimes; CI matrix

**Files:**
- Modify: `containers/Containerfile.prod` (`COPY containers/runtimes /runtimes`), `.github/workflows/main.yml` (`sandbox` job → matrix over `containers/runtimes/*.Containerfile`), `.dockerignore` (keep `containers/runtimes/`)

- [ ] **Step 1: Edit the Containerfile and the workflow**

Matrix: a first job `runtimes` lists names with `ls containers/runtimes/*.Containerfile | xargs -n1 basename | sed 's/.Containerfile//' | jq -R . | jq -sc .` into an output; the `sandbox` job uses `strategy.matrix.runtime: ${{ fromJson(needs.runtimes.outputs.names) }}`, `images: ${{ secrets.DOCKER_USERNAME }}/pywebtools-sandbox-${{ matrix.runtime }}`, `file: ./containers/runtimes/${{ matrix.runtime }}.Containerfile`, cache scope `sandbox-${{ matrix.runtime }}`.

- [ ] **Step 2: Build the app image and all three runtime images on the server (as `pytools`) and boot-test with the real secrets against a copy of the database**

Expected: `/healthz` → `{"sandbox":"ready","runtimes":{"cadquery":"ready","deps":"ready","python":"ready"}}` (images tagged locally with the production names so the inner podman finds them is not possible — inner podman pulls from the registry; therefore push first: Step 3, then boot-test with the published images).

- [ ] **Step 3: Commit and push; confirm the four CI jobs pass and Docker Hub has the three runtime repositories**

```bash
git add containers/Containerfile.prod .github/workflows/main.yml .dockerignore
git commit -m "Build every runtime Containerfile in CI; ship the runtimes folder in the app image"
git push origin main
```

- [ ] **Step 4: Boot-test the published images in a test container on the server** (same procedure as the sandbox-runner plan's Task 8): `/healthz` all ready; `POST /tool/8` → `"0x68 0x69"`; the user page renders rows with the dropdown.

### Task 9: Integration tests per runtime

**Files:**
- Modify: `server/tests/test_integration_sandbox.py`, `server/tests/test_integration_sample_tools.py` (pass runtimes: `byte_converter` → `python`, `image_to_grayscale`/`pdf_to_text`/audio → `deps`, CadQuery tools → `cadquery`)
- Create: `server/tests/test_integration_runtimes.py`

- [ ] **Step 1: Write the tests**: each runtime's self-test passes (`runner.status()` all ready); a stdlib-only tool runs in `python`; a tool importing `cv2` fails in `python` (`Outcome.OK` with `ModuleNotFoundError` text in the result, or `CRASHED`) and succeeds in `deps`; `container_with_lid` succeeds in `cadquery`; a tool with a stored sample runs via the HTTP route with no form input.
- [ ] **Step 2: Run inside the test container** with `SANDBOX_INTEGRATION=1`. Expected: all passed.
- [ ] **Step 3: Commit and push**

### Task 10: Rollout

- [ ] **Step 1:** Deploy via the timer (or `update.sh`); watch the startup log for the migration line (`added columns: …`) and the three self-tests.
- [ ] **Step 2:** Smoke: `/healthz` all ready; `POST /tool/8` → `"0x68 0x69"`; the public list still shows the nine tools; log in, open `profile`: rows show `deps` selected and `validated`; set `container_with_lid` to `cadquery`, validate it with defaults → result renders; `byte_converter` to `python`, validate → `"0x68 0x69"`.
- [ ] **Step 3:** Remove `SANDBOX_IMAGE=` from `~pytools/pywebtools/.secrets` (inside `podman unshare`, re-own `1000:1000`); update the memory note; prune the old `pywebtools-sandbox` image from the inner store on the next convenient restart.
