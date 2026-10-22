# PyTools

PyTools turns a plain Python file into a web tool. Upload a script whose entrypoint
function is named after the file, and the site builds a form from the function's
arguments, runs the script in an isolated container when someone submits the form, and
presents the return value as readable output with download links and previews.

The public instance at **https://pywebtools.com** hosts more than 240 tools, most of
them small converters and calculators of the kind that paywalled converter sites offer:
file format conversion, PDF and Office utilities, image, audio and video processing,
unit and colour conversion, hashing and encoding, network and developer helpers.

## How it works

1. **Upload.** A logged-in user uploads a `.py` file from their profile page. The server
   formats it with black, checks it against the rules below, extracts the tags from the
   first line and the entrypoint's signature, and stores it.
2. **Form.** Each argument becomes a form field: `str` a text field, `int` and `float`
   numeric fields, `Literal[...]` a list of choices, `Path` a file upload.
3. **Run.** Submitting the form starts a fresh rootless podman container from the
   sandbox image with the script, the arguments and any uploaded files. The container
   has no network, half a CPU, 1 GB of memory, a process cap and a hard time limit.
   While it runs, the page highlights the line being executed and advances a progress
   bar.
4. **Result.** The return value is rendered for people, not as a Python repr: strings
   raw with their line breaks, dicts as key/value rows, lists as bullet rows, every
   value with a `[copy]` bracket. A returned `Path` becomes a download link and, for
   images, audio, video, PDF and STL files, an inline preview. Result files are kept
   for ten minutes.

The interface is a monochrome terminal theme: the home page lists tools like `ls`,
filtering as you type by name or tag, and a tool page shows the source in a vim-style
viewer beside the argument tree. Every page carries the release version and the commit
it was built from in the bottom-right corner.

## Writing a tool

```python
# text, converter

from pathlib import Path


def lower_case_text(input: Path) -> Path:
    """Lower-case the whole of a text file."""
    output = Path("output.txt")
    output.write_text(input.read_text().lower())
    return output
```

Rules the upload enforces:

- One file; the entrypoint function has the same name as the file.
- Line 1 is a comment of comma-separated tags (letters and digits), used by search.
- Supported argument types are `str`, `int`, `float`, `Literal[...]` and `Path`.
  Anything else can be passed as a string and parsed inside the function.
- Form inputs are single-line, so multi-line content should be a `Path` upload.
- `Literal` values contain only letters, digits, `_` and `.`, and arrive as strings.
- Numeric arguments should carry a default; the form submits every field.
- A `Path` argument is always a required upload, even with a `None` default.
- The file is reformatted with `black -l 120` and stored with a single trailing
  newline. A line black cannot shorten (a long string or comment) over 120 characters
  is rejected with its line number.

Return a value the site can show: a string, number, dict, list, `Path`, or a nesting
of those. Write output files into the working directory and return their `Path`.

The sandbox image (`sandbox/pyproject.toml`) provides numpy, scipy, pandas, OpenCV
(headless, 4.x), PyAV, PyMuPDF, cadquery, ezdxf, Pillow with HEIF, PyYAML, qrcode,
openpyxl, python-docx, python-pptx, pdf2docx, mammoth, ebooklib, rawpy, markdown,
cryptography, bcrypt, fonttools, trimesh, mutagen, phonenumbers, faker, black and a
number of smaller libraries. The full list is the `dependencies` table in that file.

## Repository layout

| Path | Contents |
|---|---|
| `server/` | The FastAPI application: routes, SQLModel database, templates (htmx and hyperscript), static assets, tests. |
| `sandbox/` | The runtime that executes one tool inside its container: argument loading, result serialisation, line tracing. |
| `containers/` | `Containerfile.prod` (the app image: systemd, nested rootless podman), `Containerfile.sandbox` (the tool runtime image), app config files. |
| `tools/` | The sample tools the site started with. |
| `tools/converters/` | The 236 converter and calculator tools published on pywebtools.com. |
| `docs/` | Design documents for the sandbox runner, execution trace and runtime selection, plus `converter-backlog.md`, the ranked list of tools not built yet and why. |
| `.github/workflows/` | Builds and pushes both images on every push to `main`. |

Tool sources are written to the same standard the upload enforces: code to 120
columns, docstrings and comments wrapped at 88.

## Running the application

The application is a single container image. It needs podman with fuse and a user
namespace range, and starts with:

```bash
podman run --rm --name pywebtools \
  --device /dev/fuse --security-opt unmask=ALL \
  --memory=3g --pids-limit=4096 \
  -v ~/pywebtools/.secrets:/run/secrets/pywebtools.env:ro \
  -v ~/pywebtools/data:/data \
  -v pywebtools-inner-store:/home/podman/.local/share/containers \
  -p 8080:8080 \
  docker.io/raubcamaioni/pywebtools:latest
```

The environment file holds:

| Variable | Purpose |
|---|---|
| `SESSION_KEY` | Secret for the signed session cookie (required). |
| `DATABASE` | Path of the SQLite database, for example `/data/database.db` (required). |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI` | GitHub OAuth login. Without them the site runs with login disabled. |
| `OWNER_GITHUB_LOGIN` | The GitHub account that owns the site's own tools. |
| `ROOT_PATH` | The URL prefix the app is served under when it does not own the whole host, for example `/tools`. Empty (the default) at the root. |
| `SANDBOX_IMAGE`, `SANDBOX_TIMEOUT_SECONDS`, `SANDBOX_MEMORY`, `SANDBOX_CPUS`, `SANDBOX_PIDS`, `SANDBOX_MAX_CONCURRENT`, `SANDBOX_QUEUE_SECONDS`, `SANDBOX_RUN_DIR`, `SANDBOX_MAX_OUTPUT_MB` | Limits for tool runs; every one has a default (see `server/src/app/utility/sandbox_config.py`). |

### Serving under a sub-path

The app builds every link, asset URL, htmx call, redirect and result file link from the
prefix it is mounted at, so it can live under a path of an existing site. Set `ROOT_PATH`
to the prefix and have the reverse proxy pass requests through with the prefix intact,
for example in nginx:

```nginx
location /tools/ {
    proxy_pass http://172.18.0.1:8080;   # no trailing slash: the /tools prefix is kept
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;                 # the execution trace is a server-sent event stream
}
```

The GitHub OAuth callback then becomes `https://<host>/tools/auth/github`, in both the
OAuth app's settings and `GITHUB_REDIRECT_URI`.

`GET /healthz` reports whether the sandbox self-test has passed; tool runs return 503
until it has. The app pulls the sandbox image itself and re-checks it periodically, so
a new sandbox image is picked up without restarting the app.

## Development

```bash
cd server
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -m "not integration"      # unit tests; integration tests need a real podman
```

The tests that exercise the runner against a real nested podman and the sandbox image
are marked `integration`. The sandbox package has its own tests under `sandbox/tests`.

The stylesheet is a Tailwind build. After changing `server/src/app/webapp/static/input.css`
rebuild `output.css` with the Tailwind CLI:

```bash
tailwindcss -i server/src/app/webapp/static/input.css -o server/src/app/webapp/static/output.css --minify
```

Page-specific CSS lives inline in the templates under `templates/components/` so it
does not depend on a rebuild.

## Contributing and releasing

Work happens on branches that are merged into `main` through a pull request (squash
merge, so `main` keeps one commit per change). Every push and pull request builds both
container images in GitHub Actions to prove they build; nothing is deployed by a merge.

A release deploys:

1. Bump `version` in `server/pyproject.toml` on a branch and merge it.
2. Tag the merge commit with that version and push the tag:

   ```bash
   git tag v0.3.0 && git push origin v0.3.0
   ```

   The workflow refuses a tag that does not match the package version. It then builds
   `pywebtools` (the app) and `pywebtools-sandbox` (the runtime), pushes them to Docker
   Hub as `latest` and as the version, and the server pulls them and restarts the app,
   usually within a few minutes. The build records the commit in the app image, and
   every page shows `v<version>+<commit>` bottom-right.

To deploy without a release, open the **Actions** tab, choose **Build and publish
PyTools images**, click **Run workflow**, pick the branch and leave **publish** ticked.
That publishes the chosen branch as `latest` exactly as a release would.

Production notes for the host:

- Nested rootless podman needs cgroup delegation for the app's user. On the host,
  `/etc/systemd/system/user@.service.d/delegate.conf` should contain
  `Delegate=cpu cpuset io memory pids`, and
  `/sys/fs/cgroup/user.slice/user-<uid>.slice/cgroup.subtree_control` must list those
  controllers.
- The reasons behind every runner setting are in
  `docs/superpowers/specs/2026-10-19-podman-sandbox-runner-design.md`.

## Roadmap

- Runtime selection: let an uploader choose from several sandbox images, including
  languages other than Python (`docs/superpowers/specs/2026-10-19-runtime-selection-and-validation-design.md`).
- More converters from `docs/converter-backlog.md` as their dependencies allow.
- Remix links: share a tool with its arguments pre-filled for a specific task.
