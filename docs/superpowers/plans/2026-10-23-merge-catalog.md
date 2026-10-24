# Merge the CadQuery Catalog into PyTools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PyTools absorbs the CadQuery Catalog: models are tools with a CadQuery return, shown the catalog's way under
`?kind=model`; tags, categories and descriptions apply to every tool; `/catalog` is retired.

**Architecture:** Port the catalog's features into PyTools in three releases (runtime, metadata, models), then retire
the catalog. Most code exists in `RaubCamaioni/cadquery-catalog` `origin/main` (written `catalog:<path>` below) and is
ported with the renames listed under Global Constraints. sandboxcore gets one small feature (the declared return).

**Tech Stack:** FastAPI, SQLModel/SQLite, Jinja2, htmx, hyperscript, three.js (vendored, already in PyTools),
sandboxcore (podman sandbox), CadQuery.

**Spec:** `docs/superpowers/specs/2026-10-23-merge-catalog-design.md`

## Global Constraints

- Work in worktrees; never `checkout -b` or `add -A` in a shared checkout. Branch per release from `origin/main`.
- Renames when porting from the catalog: `Model*` tables -> `Tool*` (`ToolTag`, `ToolCategory`, `ToolDescription`),
  `model_id` -> `tool_id`, routes `/model/...` -> `/tool/...`, `/models` -> `/tools`, `/manage/model/...` ->
  `/manage/tool/...`, `catalog-admin` -> `pytools-admin`, template/text "model" -> "tool" except where it means a
  CadQuery model.
- Stored kinds are exactly `script` and `model`; the query parameter is `kind=model`. Any other `kind` value means all.
- CadQuery return annotations: `Workplane`, `Shape`, `Solid`, `Compound`, `Assembly`, bare or prefixed `cq.` or
  `cadquery.`. Nothing else is a model.
- Category rules: at most 3, first is primary, `misc` alone, none/unknown -> `misc`; slugs exactly as the spec's table.
- Tags: regex `^[a-z0-9][a-z0-9.+-]{0,29}$`, at most 10, profanity-filtered (as in the catalog).
- Lines <= 120 (`black -l 120`); LF line endings; match the surrounding comment density.
- Releases: tag `v<semver>` equal to `server/pyproject.toml` version; sandbox image before app image.
- Sandbox import trims: copy only the `vtk`/`vtkmodules` stubs, not the `ezdxf` stub (PyTools depends on real ezdxf).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; PR bodies end with the Claude Code line.

## Review Focus

1. Existing tools with a CadQuery annotation that can't build with defaults (needs a required file): untouched rows keep
   `kind=script` and still run; only a code update rebuilds. Test in Task 9.
2. A real `ezdxf` script in the merged image: `ezdxf.new()` must work (no stub). Integration test in Task 2.
3. `?kind=` with junk (`?kind=MODEL`, `?kind=<script>`): behaves as all, never a 500 or reflected markup. Test in Task 11.
4. A model edited into a script (code update without a CadQuery return), and a model deleted: stored build files are
   removed, preview/meta cleared. Test in Task 9.
5. PyTools' legacy `Tool.tags` JSON holding tags the new rules reject (uppercase, spaces, >10, duplicates): copied
   normalised or dropped, never a startup crash. Test in Task 5.

---

## Release 1: v0.4.0 runtime

### Task 1: sandboxcore reports the declared return (sandboxcore v0.2.0)

**Files:**
- Modify: `sandboxcore/src/sandboxcore/python/entrypoint.py` (`inspect_tool`)
- Modify: `sandboxcore/src/sandboxcore/signature.py` (`Signature`, `from_report`)
- Modify: `sandboxcore/pyproject.toml` (version `0.2.0`), `CHANGELOG`/README section on the report
- Test: `sandboxcore/tests/test_entrypoint.py`, `sandboxcore/tests/test_signature.py`

**Interfaces:**
- Produces: report key `"returns": str | None` (`ast.unparse` of the return annotation); `Signature.returns:
  Optional[str] = None` (last field, default None so existing constructors keep working); `from_report` keeps it if it
  is a `str` of length <= `MAX_TEXT`, else raises `SignatureError("Annotation Error: unsupported return annotation")`.
  `to_arguments`/`from_arguments` unchanged (the return is not part of the stored arguments).

- [ ] **Step 1: Write failing tests**

```python
def test_inspect_reports_return(tmp_path):
    f = tmp_path / "box.py"
    f.write_text("import cadquery as cq\ndef box(size: float = 1) -> cq.Workplane:\n    pass\n")
    assert inspect_tool(f)["returns"] == "cq.Workplane"

def test_inspect_reports_no_return(tmp_path):
    f = tmp_path / "t.py"
    f.write_text("def t(x: int = 1):\n    pass\n")
    assert inspect_tool(f)["returns"] is None

def test_from_report_keeps_returns():
    s = from_report("python", {"entrypoint": "t", "parameters": [], "returns": "cq.Workplane"})
    assert s.returns == "cq.Workplane"

def test_from_report_refuses_bad_returns():
    with pytest.raises(SignatureError):
        from_report("python", {"entrypoint": "t", "parameters": [], "returns": 5})
```

- [ ] **Step 2:** `./run-tests.sh` — the four tests fail.
- [ ] **Step 3:** Implement as in Interfaces.
- [ ] **Step 4:** `./run-tests.sh` and `./run-integration.sh` pass.
- [ ] **Step 5:** Commit, PR, merge; tag `v0.2.0`; CI publishes `raubcamaioni/sandboxcore-base:0.2.0`.

### Task 2: PyTools sandbox exports CadQuery results

**Files:**
- Create: `sandbox/src/sandbox/export.py` (from `catalog:sandbox/src/sandbox/export.py`, unchanged except the docstring)
- Create: `sandbox/src/sandbox/runner.py`
- Create: `sandbox/stubs/vtk/`, `sandbox/stubs/vtkmodules/` (from `catalog:sandbox/stubs/`, not `ezdxf/`)
- Create: `sandbox/tests/test_export.py` (from `catalog:sandbox/tests/`), `sandbox/tests/test_runner.py`
- Modify: `sandbox/pyproject.toml` (sandboxcore tag `v0.2.0`, `[project.scripts] sandbox = "sandbox.runner:main"`),
  `server/pyproject.toml` (sandboxcore tag `v0.2.0`), `containers/Containerfile.sandbox` (stubs copy, `PYTHONPATH`,
  the CadQuery version pin `RUN` from `catalog:containers/Containerfile.sandbox` lines 28-45, base image tag `0.2.0`)

**Interfaces:**
- Consumes: `sandboxcore.python.runner.main(finish=..., finish_label=...)`; `export.to_shape`, `export.export_model`.
- Produces: `finish_result(result: Any, workdir: Path | None = None) -> Any` in `runner.py`: returns
  `export_model(result, workdir)` when `is_cadquery(result)`, else `result` unchanged. `is_cadquery(value) -> bool`:
  instance of `cq.Workplane`, `cq.Shape` or `cq.Assembly`; imports cadquery lazily, only when the value's type's module
  starts with `cadquery` or `OCP` (a converter never pays the import). `main()` calls
  `run_tool(finish=finish_result, finish_label="Export Error")`.
  The model result dict keys are the catalog's: `stl`, `step`, `preview`, `meta`.

- [ ] **Step 1: Write failing tests** in `sandbox/tests/test_runner.py`:

```python
def test_plain_values_pass_through():
    assert finish_result("text") == "text"
    assert finish_result({"a": 1}) == {"a": 1}

def test_cadquery_result_is_exported(tmp_path):
    import cadquery as cq
    out = finish_result(cq.Workplane().box(1, 2, 3), tmp_path)
    assert set(out) >= {"stl", "step", "preview", "meta"} and (tmp_path / "model.stl").exists()

def test_plain_value_does_not_import_cadquery():
    sys.modules.pop("cadquery", None)
    finish_result(3)
    assert "cadquery" not in sys.modules
```

  And an integration test (marker `integration`) in `server/tests/test_integration_sample_tools.py`: a tool
  `def dxf(n: int = 1) -> str:` that runs `import ezdxf; ezdxf.new().saveas("a.dxf")` and returns the path's name
  succeeds in the built sandbox image; an existing converter (`tools/converters/json_to_yaml.py` or the nearest
  existing one) still returns its output.
- [ ] **Step 2:** Run the sandbox tests in the test image (scratchpad `cattest.sh` pattern, with the PyTools sandbox) —
  fail.
- [ ] **Step 3:** Implement; update the Containerfile.
- [ ] **Step 4:** Unit tests pass; build the sandbox image locally; integration tests pass.
- [ ] **Step 5:** Commit.

### Task 3: A model run result displays as a model

**Files:**
- Modify: `server/src/app/utility/render.py` (a model branch, from `catalog:server/src/app/utility/render.py`)
- Create: `server/src/app/webapp/templates/components/model_viewer.html` (the viewer block of
  `catalog:server/src/app/webapp/templates/pages/tool.html`: canvas, three.js STL loader script, size readout,
  STL/STEP download links)
- Modify: `server/src/app/routes/tools.py` (`_run_tool` passes a model result to the viewer render)
- Test: `server/tests/test_render.py`

**Interfaces:**
- Produces: `render.is_model_result(value) -> bool` (a dict with exactly the keys `stl`, `step`, `preview`, `meta` and
  `OutputFile` values for the first three); `render.model_result(value, root_path) -> str` (HTML of the viewer with
  download URLs from `download_url`). Other results render as today.

- [ ] **Step 1: Write failing tests**: `test_model_result_renders_viewer` (result HTML contains the viewer canvas, an
  `.stl` and a `.step` download link under `{root_path}/download/`); `test_dict_with_other_keys_renders_as_before`.
- [ ] **Step 2:** Run `test_render.py` — fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Full server suite passes. In the browser against the dev server, run a CadQuery tool returning a
  Workplane: viewer shows, STL/STEP download.
- [ ] **Step 5:** Commit; bump `server/pyproject.toml` to `0.4.0`; PR; merge.
- [ ] **Step 6: Release.** On the server, check memory: a model build and the heaviest converter run inside the 2 GB
  cap (`podman stats` while running). Tag `v0.4.0`; confirm the sandbox image deploys before the app; confirm live.

## Release 2: v0.5.0 metadata

### Task 4: The category tree

**Files:**
- Create: `server/src/app/categories.yaml` (the catalog's tree plus the spec's script categories, script categories
  first), `server/src/app/categories.py` (from `catalog:server/src/app/categories.py`)
- Test: `server/tests/test_categories.py` (from the catalog, counts updated)

**Interfaces:**
- Produces (unchanged from the catalog): `TREE`, `find(path)`, `is_leaf(path)`, `label(path)`, `leaves()`,
  `paths_under(slug)`, `MISC`, `CategoryError`.

- [ ] **Step 1:** Port the tests; change counts to 11 top-level categories plus `misc`, 40 subcategories, 41 leaves
  (40 + `misc`); add `assert label("converters/images") == "Converters › Images"` and
  `assert find("utilities/codes").name == "QR & barcodes"`.
- [ ] **Step 2:** Run — fail. **Step 3:** Port the module, write the YAML. **Step 4:** Pass. **Step 5:** Commit.

### Task 5: Metadata registry, tables and the JSON-tag copy

**Files:**
- Create: `server/src/app/metadata/__init__.py`, `tags.py`, `categories.py`, `description.py` (from the catalog, renamed)
- Modify: `server/src/app/models/tools.py` (remove the `tags` field from `Tool`; add `copy_json_tags` and
  `DoneMigration`; `search_tools` searches `ToolTag` with LIKE escaping; `del_tool` calls `metadata.delete_all`)
- Test: `test_metadata_tags.py`, `test_metadata_categories.py`, `test_metadata_description.py`,
  `test_tag_migration.py` (from the catalog, renamed); update PyTools' `test_tags.py`

**Interfaces:**
- Produces: `metadata.KINDS`, `parse_all(form)`, `save_all(session, tool_id, values)`, `apply`, `delete_all(session,
  tool_id)`, `load_all(session, tool_ids)`, `form_lists(form)`, `MetadataError`; `tags.suggest(session, prefix, limit:
  Optional[int] = 10)`; `copy_json_tags(session) -> int` (runs once at startup, reading the legacy `tool.tags` column
  with raw SQL since the field is gone).

- [ ] **Step 1:** Port the tests. Add (Review Focus 5):

```python
def test_copy_json_tags_normalises_and_drops(session):
    # legacy row: tool.tags = ["PDF", "pdf", "two words", "bad!tag", *[f"t{i}" for i in range(12)]]
    copy_json_tags(session)
    tags = Tags().load(session, [tool_id])[tool_id]
    assert tags[:2] == ["pdf", "two-words"] and len(tags) == 10 and "bad!tag" not in tags
```

- [ ] **Step 2:** Run — fail. **Step 3:** Port. **Step 4:** Full suite passes. **Step 5:** Commit.

### Task 6: Create/edit dialog and the tool page's metadata

**Files:**
- Create: `server/src/app/routes/metadata.py`; templates `model_dialog.html` (renamed `tool_dialog.html`),
  `meta_tags_editor.html`, `meta_categories_editor.html`, `meta_description_editor.html`,
  `meta_description_display.html`, `model_meta.html` (renamed `tool_meta.html`), `meta_style.html`;
  `webapp/scripts/meta-editors.js` (all from the catalog)
- Modify: `server/src/app/routes/upload.py` (`tool_create` at `POST /manage/tool/upload`, file required;
  `tool_update` at `POST /manage/tool/update/{id}`, file optional, admin may edit metadata but not code, banned 403),
  `pages/user.html` (the `<dialog id="tool-dialog">`), `upload_tool_item.html` ([create]), `update_tool_item.html`
  ([edit]), `pages/tool.html` (description above the code, tags and categories)
- Test: `test_metadata_routes.py` (from the catalog), PyTools' upload tests updated to the new form fields

**Interfaces:**
- Consumes: Task 5's registry. Produces: `GET /manage/tool/create`, `GET /manage/tool/{id}/edit` (dialog HTML),
  `GET /tags/suggest?q=` (`[{"tag","count"}]`, all tags when `q` is empty, 50 otherwise).

- [ ] **Step 1:** Port tests; they fail. **Step 2:** Port code and templates. **Step 3:** Suite passes.
- [ ] **Step 4:** Browser check on the dev server: create a tool with tags/categories/description; edit it; the
  `[+]`, chip box, dropdown scrolling and `[cancel] [save]` behave as in catalog v0.6.4. **Step 5:** Commit.

### Task 7: Browse by category

**Files:**
- Modify: `server/src/app/routes/tools.py` (`/c/{cat}`, `/c/{cat}/{sub}`, `category_counts`, `index_page` from
  `catalog:server/src/app/routes/browse.py`, or create `routes/browse.py` as the catalog does), `pages/index.html`
  (category bar)
- Test: `test_browse.py` (from the catalog)

- [ ] **Step 1:** Port tests — fail. **Step 2:** Port. **Step 3:** Pass; browser check. **Step 4:** Commit.

### Task 8: apply-manifest and filing the existing tools

**Files:**
- Create: `server/src/app/admin_cli.py` (from the catalog; entry point `pytools-admin = "app.admin_cli:main"` in
  `server/pyproject.toml`), `tools/catalog.yaml`
- Test: `test_admin_cli.py`, `test_manifest.py` (from the catalog; `test_manifest` covers `tools/*.py` and
  `tools/converters/*.py`)

**Interfaces:**
- Produces: `apply_manifest(session, manifest, owner, apply: bool, backup_dir: Path) -> list[str]` (the change lines),
  manifest entry `{file, categories, tags, description?}` keyed by tool name.

- [ ] **Step 1:** Port tests — fail. **Step 2:** Port the CLI. **Step 3:** Draft `tools/catalog.yaml` for every repo
  tool (categories from the spec's tree, up to 10 tags, a one-line description). **Step 4:** Suite passes.
- [ ] **Step 5:** Bump to `0.5.0`, PR (the user reviews the filing), merge, tag `v0.5.0`, confirm live.
- [ ] **Step 6:** On the server: dry run, then `--apply` (backup written); check counts per category in the live
  category bar.

## Release 3: v0.6.0 models

### Task 9: Tool kind, the upload build and stored builds

**Files:**
- Modify: `server/src/app/models/tools.py` (`Tool.kind: str = "script"`, `Tool.preview_svg: str = ""`, `Tool.meta:
  dict` JSON; `ensure_columns(engine)` adds missing columns with `ALTER TABLE tool ADD COLUMN` at startup, since
  `create_all` does not alter existing tables), `server/src/app/__init__.py` (`MODELS_DIR` as the catalog has it),
  `server/src/app/routes/upload.py` (`validate_model`, `store_default_build` from the catalog), `server/src/app/
  routes/tools.py` (`build_model`, `build_failure` from the catalog)
- Create: `server/src/app/models/kind.py`
- Test: `server/tests/test_model_kind.py`, `test_build_files.py` and `test_upload_models.py` (from the catalog)

**Interfaces:**
- Produces: `kind.declares_model(returns: Optional[str]) -> bool`; on create and on a code update, `declares_model`
  -> `validate_model` (400 `Model Build Failed: ...` and nothing stored on failure) -> `store_default_build` ->
  `kind="model"`; otherwise `kind="script"`, `preview_svg=""`, `meta={}` and `MODELS_DIR/<id>` removed.
  `del_tool` removes `MODELS_DIR/<id>`.

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.parametrize("ann", ["cq.Workplane", "Workplane", "cadquery.Shape", "Solid", "cq.Compound", "Assembly"])
def test_declares_model(ann):
    assert declares_model(ann)

@pytest.mark.parametrize("ann", [None, "str", "Path", "cq.Vector", "list[cq.Workplane]", "Workplanes"])
def test_not_a_model(ann):
    assert not declares_model(ann)
```

  Route tests: a declared model with defaults is stored with `kind == "model"` and files on disk; a declared model whose
  build fails gets 400 and no row; a plain script is `kind == "script"` with no build; (Review Focus 4) updating a model
  with script code clears `preview_svg`/`meta` and removes its files, and deleting a model removes them; (Review Focus
  1) a pre-existing row created before the column (inserted with raw SQL, no `kind`) reads as `script` and runs.
- [ ] **Step 2:** Run — fail. **Step 3:** Implement. **Step 4:** Suite passes. **Step 5:** Commit.

### Task 10: The model page

**Files:**
- Modify: `server/src/app/routes/tools.py` (`/tool/{id}` renders the model layout when `kind == "model"`; add
  `GET /tool/{id}/preview.svg` and `GET /tool/{id}/model.{ext}` for `stl`/`step`, from the catalog's
  `model_preview`/`model_default_file`, same visibility checks), `pages/tool.html` (model layout from the catalog:
  viewer on the stored default build, parameter panel with rebuild, STL/STEP links, size/volume readout, code
  viewable)
- Test: `test_tool_routes.py` (model page cases from the catalog's)

- [ ] **Step 1:** Port/add tests (model page shows the viewer and default-build links; a private model's files 404
  for others; a script page has no viewer) — fail. **Step 2:** Implement. **Step 3:** Pass; browser check: open a
  model, rebuild with new parameters, download STL/STEP. **Step 4:** Commit.

### Task 11: Listings with kind

**Files:**
- Modify: `routes/tools.py` (`/`, `/c/...`, `POST /tools` accept `kind`; `normalise_kind(value) -> Optional[str]`
  returns `"model"` only for exactly `"model"`), `components/index_tool_item.html` (thumbnail `<img>` from
  `/tool/{id}/preview.svg` when `kind == "model"`), `components/index_model_card.html` (the catalog's card),
  `pages/index.html` (card grid when `kind=model`; header switch `[all] [models]`; every category, search and paging
  link keeps `kind`), `category_counts(session, kind)`
- Test: `test_browse.py` additions

- [ ] **Step 1: Write failing tests**: `?kind=model` lists only models as cards; no `kind` lists both with a thumbnail
  only on model rows; category links and the paging loader on a `kind=model` page carry `kind=model`; category counts
  under `kind=model` count only models, and a category with no models is absent from the bar under `kind=model` but
  present (if it has scripts) without it; (Review Focus 3) `?kind=MODEL`, `?kind=<b>x</b>` and `?kind=` render the all
  view with status 200 and no `<b>x</b>` in the page.
- [ ] **Step 2:** Run — fail. **Step 3:** Implement. **Step 4:** Pass; browser check of both views and the switch.
  **Step 5:** Commit.

### Task 12: Move the models in and create them live

**Files:**
- Create: `tools/models/*.py` (the 130 files from `catalog:models/`), their entries in `tools/catalog.yaml` (from
  `catalog:models/catalog.yaml`, categories unchanged)
- Modify: `server/src/app/admin_cli.py` (`apply_manifest` creates a missing tool), `test_admin_cli.py`,
  `test_manifest.py` (also covers `tools/models/`)

**Interfaces:**
- `apply_manifest(..., create_missing: bool = True, sandbox=...)`: an entry with no tool of that name owned by `owner`
  is created through the same function the upload route uses (`_create_tool` + `validate_model` +
  `store_default_build`), set public, then given its metadata; a build failure is reported as a change line
  `FAILED <name>: <reason>` and does not stop the run.

- [ ] **Step 1: Write failing tests**: a missing entry is created (dry run reports `create <name>` and writes
  nothing); a second `--apply` creates nothing; a failing build is reported and the rest still apply.
- [ ] **Step 2:** Run — fail. **Step 3:** Implement; copy the models and manifest entries. **Step 4:** Suite passes.
- [ ] **Step 5:** Bump to `0.6.0`, PR, merge, tag `v0.6.0`, confirm live.
- [ ] **Step 6:** On the server: dry run (expect 130 creates, no failures), `--apply`, then check
  `https://raubcamaioni.com/tools/?kind=model` in the browser against `/catalog`.

## Retire the catalog

### Task 13: Shut down `/catalog`

- [ ] **Step 1:** Remove the `/catalog` location from the nginx config (the docker nginx on the server); `nginx -t`;
  reload; `curl -sI https://raubcamaioni.com/catalog/` returns 404; `/tools/` still 200.
- [ ] **Step 2:** As `pytools`: `systemctl --user disable --now catalog.service catalog-update.timer`.
- [ ] **Step 3:** Final backup of `~pytools/catalog/data` to `/root/server-backup-*`; keep until the user confirms
  `?kind=model`, then delete the data directory, the `catalog-inner-store` volume and the catalog images.
- [ ] **Step 4:** Archive `RaubCamaioni/cadquery-catalog` (`gh repo archive`), with the user's go-ahead; tell the user
  to delete the catalog's GitHub OAuth app.
- [ ] **Step 5:** Update memory: catalog retired, models live in PyTools under `?kind=model`.
