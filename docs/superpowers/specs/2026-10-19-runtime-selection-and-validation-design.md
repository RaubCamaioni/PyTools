# Runtime selection and tool validation

Date: 2026-10-19
Status: design for review
Builds on: `2026-10-19-podman-sandbox-runner-design.md` (the sandbox runner this extends)

## Goal

An uploader chooses which sandbox image their tool runs in from a fixed, inspectable
list, supplies default working inputs (including sample files), and the site runs the
tool once with those inputs before anyone else can see it. Tools that have not passed
that validation are visible only to their owner.

Success: the three runtimes build and self-test on the server; the nine existing tools
keep working unchanged; a new upload cannot appear in the public list until a
validation run has succeeded in its chosen runtime; the uploader can read exactly which
packages a runtime provides before choosing it.

## Runtimes are files

```
containers/
  Containerfile.prod            the web app (unchanged)
  app/                          its config files (unchanged)
  runtimes/
    python.Containerfile        → docker.io/raubcamaioni/pywebtools-sandbox-python
    deps.Containerfile          → docker.io/raubcamaioni/pywebtools-sandbox-deps
    cadquery.Containerfile      → docker.io/raubcamaioni/pywebtools-sandbox-cadquery
```

- A runtime's **name** is its file name without `.Containerfile`; that name is what the
  dropdown shows, what the database stores, and the image name suffix.
- Every runtime Containerfile is written to be read by uploaders: a comment block at the
  top saying what it is for, a single explicit `pip install` line listing the packages,
  no build arguments, no includes. All three start from `python:3.12-slim-bookworm`,
  create the unprivileged `app` user (uid 1001), install the `sandbox` package into
  `/venvs/sandbox`, and use `/venvs/sandbox/bin/sandbox` as entrypoint, exactly like
  today's single image.
- Contents: `python` installs nothing beyond the sandbox runner; `deps` adds numpy,
  scipy, pandas, opencv-python, av, pymupdf, pydantic, pyparsing; `cadquery` adds
  cadquery and ezdxf on top of `deps`. The `sandbox` package's own dependency list is
  reduced to what the runner needs (nothing beyond the standard library), so the
  `python` image stays small.
- The app image copies `containers/runtimes/` to `/runtimes`. At startup the app lists
  `/runtimes/*.Containerfile`, sorted by name; that list is the single source of truth
  for the dropdown, the image names and the startup self-tests. Adding a runtime later
  means adding one file and pushing.
- Images: `SANDBOX_IMAGE_PREFIX` (default `docker.io/raubcamaioni/pywebtools-sandbox-`)
  + name + `:latest`. CI builds every file in the folder (a matrix over the folder's
  contents) and publishes `latest`, `main` and `sha-<short>` tags for each.
- All runtimes share the same limits: `SANDBOX_TIMEOUT_SECONDS` (production: 30),
  0.5 CPU, 1 GB, 64 pids, no network.

## Data

`tool` gains:

| Column | Type | Default | Meaning |
|---|---|---|---|
| `runtime` | text | `deps` | runtime name; must match a file in `/runtimes` |
| `defaults` | JSON | `{}` | argument name → default value; for `Path` arguments the sample file's name |
| `validated` | bool | `false` | a validation run succeeded with the current code, runtime and defaults |
| `source` | text | `upload` | reserved: `upload` now, `github` in a later design |
| `source_ref` | text, nullable | `null` | reserved for the GitHub design |

Sample files live at `/data/tools/<tool id>/samples/<file name>` on the existing data
volume (owned by the app user; the sandbox gets a copy in its run directory).

**Migration.** SQLModel's `create_all` never alters an existing table, so startup runs an
idempotent migration before serving: for each new column missing from `tool` (checked
with `PRAGMA table_info`), `ALTER TABLE tool ADD COLUMN …` with the default above.
Existing rows therefore become `runtime=deps, validated=true, defaults={}`: they keep
working exactly as today and the owner can re-validate them from the creator tab at
leisure.

## Visibility rules

- **Public list and tool page:** a tool is shown to a visitor only when
  `public and validated`. For anyone but the owner an unvalidated tool is a 404,
  exactly like a private one today.
- **Owner:** always sees and can run their own tools, validated or not.
- **Public toggle:** `POST /manage/tool/settings/{id}?public=true` is refused
  (`400 Validate the tool first`) while `validated` is false; updating the code (see
  below) can therefore take a tool off the public list, never put it on.

## The creator tab

The user page gets a **creator** section (above the tool list) that handles upload,
configuration and validation in one place:

1. **Upload** a `.py` file as today. The tool is created with `validated=false`,
   `runtime=deps`, `defaults` pre-filled from the function signature's own defaults.
2. The new tool's row expands into the **configure panel**:
   - runtime dropdown listing the runtime names, with a `[ dependencies ]` toggle that
     shows the selected runtime's Containerfile verbatim in a code block
     (`GET /runtimes/{name}` returns it as text; the panel fetches it with htmx);
   - the tool's argument form, the same component the tool page renders, pre-filled
     with the current `defaults`; `Path` arguments are file pickers that show the stored
     sample's name when one exists;
   - `[ validate ]`.
3. **Validate** (`POST /manage/tool/validate/{id}`, owner only, multipart): stores the
   chosen runtime and the submitted defaults, saves any uploaded sample files under the
   tool's samples directory (replacing same-named files), then runs the tool through the
   normal runner in that runtime with those inputs. The rendered result (or the failure
   message and stderr tail, as a visitor would see it) is swapped into the panel.
   Success sets `validated=true`; failure leaves or sets it `false`. Validation can be
   repeated at any time.
4. The row shows `validated` / `not validated` and, when validated, the public and
   anonymous toggles as today.
5. **Updating the code** (`POST /manage/tool/update/{id}`) keeps runtime and defaults,
   sets `validated=false`, and immediately re-runs validation with the stored defaults;
   the response is the validation result. A code change that breaks the tool thus
   removes it from the public list instead of breaking it for visitors.

## Running a tool

- `PodmanRunner.run(tool, run_dir, runtime)` picks the image for the runtime. An
  unknown runtime (a file removed since the tool was configured) is reported as
  `503 Sandbox unavailable` for that tool, and the owner sees
  `runtime "<name>" no longer exists` in the creator tab.
- **Tool page form** is pre-filled from `defaults`. A `Path` argument shows
  `sample: <file name>` next to the picker; if the visitor submits without choosing a
  file, the stored sample is copied into the run directory and used. All other
  arguments behave as today (the submitted form value, or the default).

## Startup and health

- Startup discovers the runtimes, then for **each** image: pull (local copy acceptable
  if the pull fails), then the existing memory and timeout self-test. A runtime whose
  image is missing or whose self-test fails is marked unavailable with its reason; the
  others serve normally. The 60 s retry loop re-tries only the unavailable runtimes; the
  10-minute refresh loop pulls every image.
- `/healthz` returns `{"sandbox": "ready", "runtimes": {"python": "ready", "deps":
  "ready", "cadquery": "ready"}}` with 200, or 503 with `"sandbox": "degraded"` /
  `"unavailable"` and the per-runtime reasons.
- The first startup after this release pulls three images instead of one (the
  `cadquery` image is today's size, the others smaller); tool runs on a runtime return
  503 until that runtime's self-test passes, pages serve throughout.

## CI

The workflow's `sandbox` job becomes a matrix over `containers/runtimes/*.Containerfile`
(the list is read from the checkout in a first job step), building and pushing
`pywebtools-sandbox-<name>` for each. The `app` job is unchanged. The old single
`pywebtools-sandbox` repository on Docker Hub is left alone and no longer pulled.

## Testing

- **Unit** (fakes, as in the runner suite): runtime discovery from a temp folder;
  per-runtime availability, `/healthz` per-runtime output, `run()` image selection and
  the unknown-runtime path; the migration on a database created with the old schema;
  visibility rules (public list, tool page 404, public toggle refusal); the validate
  route (success → validated, failure → not, sample files stored, defaults stored);
  update resets and re-validates; the tool page pre-fills defaults and uses a sample
  when no file is submitted; `GET /runtimes/{name}` returns the file and 404 otherwise.
- **Integration** (inside the app container, `SANDBOX_INTEGRATION=1`): each runtime
  passes the self-test; `byte_converter` runs in `python`, `image_to_grayscale` in
  `deps`, `container_with_lid` in `cadquery`; a tool with a stored sample file runs
  with no form input.
- **Deploy smoke:** `/healthz` lists all three runtimes ready; `POST /tool/8` returns
  `"0x68 0x69"`; the public list still shows the nine existing tools.

## Out of scope

Tools sourced from GitHub repositories (only the `source` columns are reserved), the
offline executable, per-runtime resource limits, user-supplied images.

## Risks

- Three images instead of one on a 79 GB disk: the inner image store grows by roughly
  the size of the `deps` and `python` images (the `cadquery` image replaces today's).
  The refresh loop still does not prune old layers; that remains the deferred minor
  from the runner review.
- Sample files are stored outside the database; a database backup without
  `/data/tools/` loses the samples, not the tools. The existing data volume already
  holds both.
