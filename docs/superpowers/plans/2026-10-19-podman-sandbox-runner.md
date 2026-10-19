# Podman-in-podman Sandbox Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `isolate` with per-run rootless podman containers launched by a podman inside the app container, enforcing 0.5 CPU / 1 GB / 64 pids / 10 s per tool run with no network.

**Architecture:** A new `PodmanRunner` in `app/utility/sandbox.py` builds and supervises one `podman run` per tool execution, classifies the outcome (ok / timeout / out-of-memory / crashed), and gates concurrency with a semaphore. The app image becomes a `ubi9/ubi-init` systemd container whose `podman` user owns a delegated systemd user session; a separate `pywebtools-sandbox` image holds the tool runtime. Startup verifies limits are enforced and fails closed.

**Tech Stack:** Python 3.12 (package floor 3.10), FastAPI/Starlette 1.x, asyncio subprocesses, pytest + pytest-asyncio, podman 5 (RHEL 9 AppStream), systemd, fuse-overlayfs, GitHub Actions → Docker Hub.

**Spec:** `docs/superpowers/specs/2026-10-19-podman-sandbox-runner-design.md`

## Global Constraints

- Sandbox limits, verbatim from the spec: `--network=none --uts=host --user=1001 --cpus=0.5 --memory=1g --memory-swap=1g --pids-limit=64 --read-only --tmpfs /tmp:rw,size=64m --cap-drop=ALL --security-opt=no-new-privileges --timeout=10`, run dir mounted at its own path `-v <dir>:<dir>:U` (absolute upload/result paths must resolve on both sides).
- Concurrency 2, queue wait 10 s, app-side safety net 12 s, re-pull of the sandbox image every 10 min, readiness wait up to 60 s, pull retry every 60 s.
- User-facing messages, verbatim: `Tool exceeded the 10 second limit`, `Tool exceeded the 1 GB memory limit`, `Tool failed to run`, `Server busy, try again`, `Sandbox unavailable`.
- Environment variables and defaults: `SANDBOX_IMAGE=docker.io/raubcamaioni/pywebtools-sandbox:latest`, `SANDBOX_MAX_CONCURRENT=2`, `SANDBOX_QUEUE_SECONDS=10`, `SANDBOX_TIMEOUT_SECONDS=10`, `SANDBOX_MEMORY=1g`, `SANDBOX_CPUS=0.5`, `SANDBOX_PIDS=64`, `SANDBOX_RUN_DIR=/tmp/pywebtools-runs`. `SANDBOX` (old venv path) is removed.
- Server package stays `requires-python >= 3.10`; no new runtime dependencies (tests add `pytest`, `pytest-asyncio` as a `dev` extra only).
- `newuidmap`/`newgidmap` in the app image keep their file capability; never `chmod u+s` them.
- Images and tags: `raubcamaioni/pywebtools` and `raubcamaioni/pywebtools-sandbox`, tags `latest`, `main`, `sha-<short>`; publish only on pushes to `main`.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; push to `main` is allowed (owner's instruction).
- Tests run from `server/`: `cd server && python -m pytest`. Integration tests are selected with `-m integration` and skip unless `SANDBOX_INTEGRATION=1`.

## Review Focus

1. `result.json` present but empty or malformed → user sees `Tool failed to run`, never a 500. Test in Task 3 (`test_classify_malformed_result_is_crashed`) and Task 6 (`test_run_tool_malformed_result_renders_failure`).
2. Run directory names from `secret_dir_name` may start with `-` or `_`; the container name must still be valid and the volume argument must not be parsed as a flag. Test in Task 2 (`test_command_name_and_volume_with_leading_dash`).
3. `podman inspect` fails because the container vanished (e.g. podman restarted) → classified `CRASHED`, `rm -f` still attempted, no exception escapes. Test in Task 4 (`test_run_inspect_failure_is_crashed`).
4. While the sandbox is unavailable (self-test failed, image missing) a request must get `503 Sandbox unavailable` immediately without taking a slot or writing files. Test in Task 6 (`test_run_tool_unavailable_returns_503_without_slot`).
5. Timeout path: `podman run` returns late and the safety net fires → exactly one `kill`, exactly one `rm -f`, and `unshare chown` still runs so cleanup can delete the directory. Test in Task 4 (`test_run_safety_net_kills_once_and_cleans_up`).

---

### Task 1: Test scaffolding and sandbox configuration

**Files:**
- Modify: `server/pyproject.toml` (add `[project.optional-dependencies] dev`, `[tool.pytest.ini_options]`)
- Modify: `server/src/app/__init__.py:10-21` (`_ENVIRONMENT`)
- Create: `server/tests/__init__.py` (empty), `server/tests/conftest.py`
- Create: `server/src/app/utility/sandbox_config.py`
- Test: `server/tests/test_sandbox_config.py`

**Interfaces:**
- Produces: `app.utility.sandbox_config.SandboxConfig` (frozen dataclass) with fields `image: str`, `max_concurrent: int`, `queue_seconds: float`, `timeout_seconds: float`, `memory: str`, `cpus: str`, `pids: int`, `run_dir: Path`; `SandboxConfig.from_environment(env: Mapping[str, str]) -> SandboxConfig`; property `memory_label -> str` (`"1g"` → `"1 GB"`, `"512m"` → `"512 MB"`, anything else returned unchanged).
- Produces: `_ENVIRONMENT` no longer requires `SANDBOX`; `ENVIRONMENT.sandbox: SandboxConfig` built from `os.environ`.

- [ ] **Step 1: Add dev extra and pytest config to `server/pyproject.toml`**

```toml
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.24"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: needs a real inner podman and the sandbox image"]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `server/tests/conftest.py`**

Set the mandatory secrets before `app` is imported so `_ENVIRONMENT.__post_init__` passes:

```python
import os
for key in ("SESSION_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"):
    os.environ.setdefault(key, "test")
os.environ.setdefault("DATABASE", ":memory:")
```

- [ ] **Step 3: Write the failing tests `server/tests/test_sandbox_config.py`**

```python
from pathlib import Path
from app.utility.sandbox_config import SandboxConfig

def test_defaults_from_empty_environment():
    cfg = SandboxConfig.from_environment({})
    assert cfg.image == "docker.io/raubcamaioni/pywebtools-sandbox:latest"
    assert (cfg.max_concurrent, cfg.queue_seconds, cfg.timeout_seconds) == (2, 10.0, 10.0)
    assert (cfg.memory, cfg.cpus, cfg.pids) == ("1g", "0.5", 64)
    assert cfg.run_dir == Path("/tmp/pywebtools-runs")

def test_overrides_from_environment():
    cfg = SandboxConfig.from_environment({"SANDBOX_MAX_CONCURRENT": "3", "SANDBOX_MEMORY": "512m", "SANDBOX_RUN_DIR": "/runs"})
    assert cfg.max_concurrent == 3 and cfg.memory == "512m" and cfg.run_dir == Path("/runs")

def test_memory_label():
    assert SandboxConfig.from_environment({}).memory_label == "1 GB"
    assert SandboxConfig.from_environment({"SANDBOX_MEMORY": "512m"}).memory_label == "512 MB"

def test_environment_no_longer_requires_sandbox_path(monkeypatch):
    monkeypatch.delenv("SANDBOX", raising=False)
    import importlib, app
    importlib.reload(app)
    assert app.ENVIRONMENT.sandbox.max_concurrent == 2
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd server && pip install -e .[dev] && python -m pytest tests/test_sandbox_config.py -v`
Expected: FAIL with `ModuleNotFoundError: app.utility.sandbox_config`

- [ ] **Step 5: Implement `SandboxConfig` in `server/src/app/utility/sandbox_config.py` and wire `_ENVIRONMENT`**

In `app/__init__.py`: remove the `SANDBOX` field, keep the `None` check for the remaining fields, and add `sandbox: SandboxConfig = field(default_factory=lambda: SandboxConfig.from_environment(os.environ))`. `sandbox_config.py` must not import `app` (it is imported by it).

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_sandbox_config.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add server/pyproject.toml server/tests server/src/app/__init__.py server/src/app/utility/sandbox_config.py
git commit -m "Add sandbox configuration from environment and pytest scaffolding"
```

### Task 2: Podman command builder

**Files:**
- Create: `server/src/app/utility/podman_runner.py`
- Test: `server/tests/test_podman_command.py`

**Interfaces:**
- Consumes: `SandboxConfig` (Task 1).
- Produces: `PodmanRunner.__init__(self, config: SandboxConfig, exec: Exec | None = None)`; `PodmanRunner.command(self, name: str, tool: Path, run_dir: Path) -> list[str]`; `PodmanRunner.container_name(run_dir: Path) -> str` (static) returning `f"run-{run_dir.name}"`; module type alias `Exec = Callable[..., Awaitable[tuple[int, str, str]]]` (argv → returncode, stdout, stderr).

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
from app.utility.sandbox_config import SandboxConfig
from app.utility.podman_runner import PodmanRunner

CFG = SandboxConfig.from_environment({})

def test_command_matches_spec_flags():
    r = PodmanRunner(CFG)
    cmd = r.command("run-abc", Path("/tmp/pywebtools-runs/abc/tool.py"), Path("/tmp/pywebtools-runs/abc"))
    assert cmd[:3] == ["podman", "run", "--name"] and cmd[3] == "run-abc"
    for flag in ["--network=none", "--uts=host", "--userns=auto", "--cpus=0.5", "--memory=1g", "--memory-swap=1g",
                 "--pids-limit=64", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--timeout=10"]:
        assert flag in cmd
    assert cmd[cmd.index("--tmpfs") + 1] == "/tmp:rw,size=64m"
    assert cmd[cmd.index("-v") + 1] == "/tmp/pywebtools-runs/abc:/box:U"
    assert cmd[-5:] == [CFG.image, "--file", "/box/tool.py", "--workdir", "/box"]
    assert "--rm" not in cmd

def test_command_name_and_volume_with_leading_dash():
    run_dir = Path("/tmp/pywebtools-runs/-_weird")
    name = PodmanRunner.container_name(run_dir)
    assert name == "run--_weird"
    cmd = PodmanRunner(CFG).command(name, run_dir / "t.py", run_dir)
    assert cmd[cmd.index("-v") + 1].startswith("/tmp/pywebtools-runs/-_weird:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_podman_command.py -v`
Expected: FAIL with `ModuleNotFoundError: app.utility.podman_runner`

- [ ] **Step 3: Implement `PodmanRunner.__init__`, `container_name`, `command` in `podman_runner.py`**

The timeout flag uses `int(config.timeout_seconds)`. Store `exec` for later tasks; default to `None` for now.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_podman_command.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/podman_runner.py server/tests/test_podman_command.py
git commit -m "Build the per-run podman command from sandbox configuration"
```

### Task 3: Outcome classification

**Files:**
- Modify: `server/src/app/utility/podman_runner.py`
- Test: `server/tests/test_podman_outcome.py`

**Interfaces:**
- Produces: `class Outcome(Enum): OK, TIMEOUT, OOM, CRASHED`; `@dataclass class RunResult: outcome: Outcome; results: Any = None; message: str | None = None; stderr_tail: str = ""`; `PodmanRunner.classify(self, run_dir: Path, exit_code: int | None, oom_killed: bool, elapsed: float, stderr: str, timed_out: bool = False) -> RunResult` (`timed_out` is set by `run` when its safety net fired).
- `results` is the deserialized `result.json` (via `app.utility.serializer.load`) when `outcome is OK`.

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path
from app.utility.sandbox_config import SandboxConfig
from app.utility.podman_runner import PodmanRunner, Outcome

CFG = SandboxConfig.from_environment({})

def classify(tmp_path, **kw):
    kw = {"exit_code": 0, "oom_killed": False, "elapsed": 0.5, "stderr": ""} | kw
    return PodmanRunner(CFG).classify(tmp_path, **kw)

def test_result_json_means_ok_even_with_nonzero_exit(tmp_path):
    (tmp_path / "result.json").write_text(json.dumps("hello"))
    r = classify(tmp_path, exit_code=1)
    assert r.outcome is Outcome.OK and r.results == "hello" and r.message is None

def test_oom_killed(tmp_path):
    r = classify(tmp_path, exit_code=137, oom_killed=True)
    assert r.outcome is Outcome.OOM and r.message == "Tool exceeded the 1 GB memory limit"

def test_timeout_by_elapsed(tmp_path):
    r = classify(tmp_path, exit_code=137, elapsed=10.2)
    assert r.outcome is Outcome.TIMEOUT and r.message == "Tool exceeded the 10 second limit"

def test_timeout_by_safety_net_flag(tmp_path):
    assert classify(tmp_path, exit_code=None, elapsed=0.0, timed_out=True).outcome is Outcome.TIMEOUT

def test_crash_keeps_stderr_tail(tmp_path):
    r = classify(tmp_path, exit_code=1, stderr="\n".join(f"line{i}" for i in range(40)))
    assert r.outcome is Outcome.CRASHED and r.message == "Tool failed to run"
    assert r.stderr_tail.splitlines() == [f"line{i}" for i in range(20, 40)]

def test_classify_malformed_result_is_crashed(tmp_path):
    (tmp_path / "result.json").write_text("{not json")
    assert classify(tmp_path).outcome is Outcome.CRASHED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_podman_outcome.py -v`
Expected: FAIL with `ImportError: cannot import name 'Outcome'`

- [ ] **Step 3: Implement `Outcome`, `RunResult`, `PodmanRunner.classify`**

Order of checks: valid `result.json` → OK; `oom_killed` → OOM; `timed_out or elapsed >= timeout_seconds - 0.5` → TIMEOUT; else CRASHED. `stderr_tail` is the last 20 lines. Messages use `config.memory_label` and `f"{config.timeout_seconds:g}"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_podman_outcome.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/podman_runner.py server/tests/test_podman_outcome.py
git commit -m "Classify sandbox run outcomes into ok, timeout, oom and crashed"
```

### Task 4: Supervised run with slots

**Files:**
- Modify: `server/src/app/utility/podman_runner.py`
- Test: `server/tests/test_podman_run.py`

**Interfaces:**
- Produces: `class SandboxBusy(Exception)`, `class SandboxUnavailable(Exception)`; `async PodmanRunner.run(self, tool: Path, run_dir: Path) -> RunResult`; `PodmanRunner.available: bool` (property, `True` by default until Task 5 wires startup) and `PodmanRunner.unavailable_reason: str | None`; module function `async run_podman(*argv: str, timeout: float | None = None) -> tuple[int, str, str]` (the default `Exec`, uses `asyncio.create_subprocess_exec` with captured output; raises `asyncio.TimeoutError` on `timeout`).
- Podman subcommands issued by `run`, in order: `run …` (with `timeout=config.timeout_seconds + 2`), on timeout `kill <name>`; then `inspect --format {{.State.ExitCode}} {{.State.OOMKilled}} <name>`, `logs --tail 20 <name>`, `rm -f <name>`, `unshare chown -R 0:0 <run_dir>`.

- [ ] **Step 1: Write the failing tests**

```python
import asyncio, json
from pathlib import Path
import pytest
from app.utility.sandbox_config import SandboxConfig
from app.utility.podman_runner import PodmanRunner, Outcome, SandboxBusy, SandboxUnavailable

class FakePodman:
    """Records argv; `responses` maps subcommand -> (rc, out, err) or an exception."""
    def __init__(self, responses=None, run_delay=0.0):
        self.calls, self.responses, self.run_delay = [], responses or {}, run_delay
    async def __call__(self, *argv, timeout=None):
        self.calls.append(list(argv))
        sub = argv[1]
        if sub == "run":
            if timeout is not None and self.run_delay > timeout: raise asyncio.TimeoutError
            await asyncio.sleep(self.run_delay)
        resp = self.responses.get(sub, (0, "", ""))
        if isinstance(resp, Exception): raise resp
        return resp
    def subcommands(self): return [c[1] for c in self.calls]

def cfg(**kw): return SandboxConfig.from_environment({k: str(v) for k, v in kw.items()})

async def test_run_happy_path_sequence_and_result(tmp_path):
    (tmp_path / "result.json").write_text(json.dumps([1, 2]))
    fake = FakePodman({"inspect": (0, "0 false", "")})
    r = await PodmanRunner(cfg(), exec=fake).run(tmp_path / "t.py", tmp_path)
    assert r.outcome is Outcome.OK and r.results == [1, 2]
    assert fake.subcommands() == ["run", "inspect", "logs", "rm", "unshare"]
    assert fake.calls[-1] == ["podman", "unshare", "chown", "-R", "0:0", str(tmp_path)]
    assert fake.calls[-2][:4] == ["podman", "rm", "-f", f"run-{tmp_path.name}"]

async def test_run_oom_from_inspect(tmp_path):
    fake = FakePodman({"inspect": (0, "137 true", "")})
    r = await PodmanRunner(cfg(), exec=fake).run(tmp_path / "t.py", tmp_path)
    assert r.outcome is Outcome.OOM

async def test_run_safety_net_kills_once_and_cleans_up(tmp_path):
    # run_delay > timeout makes the fake raise asyncio.TimeoutError, like a hung `podman run`
    fake = FakePodman({"inspect": (0, "137 false", "")}, run_delay=5.0)
    r = await PodmanRunner(cfg(SANDBOX_TIMEOUT_SECONDS=0.1), exec=fake).run(tmp_path / "t.py", tmp_path)
    assert r.outcome is Outcome.TIMEOUT
    assert fake.subcommands().count("kill") == 1 and fake.subcommands().count("rm") == 1
    assert fake.subcommands()[-1] == "unshare"

async def test_run_inspect_failure_is_crashed(tmp_path):
    fake = FakePodman({"inspect": (125, "", "no such container")})
    r = await PodmanRunner(cfg(), exec=fake).run(tmp_path / "t.py", tmp_path)
    assert r.outcome is Outcome.CRASHED and "rm" in fake.subcommands()

async def test_run_busy_after_queue_wait(tmp_path):
    fake = FakePodman({"inspect": (0, "0 false", "")}, run_delay=0.5)
    runner = PodmanRunner(cfg(SANDBOX_MAX_CONCURRENT=1, SANDBOX_QUEUE_SECONDS=0.05), exec=fake)
    first = asyncio.create_task(runner.run(tmp_path / "a.py", tmp_path))
    await asyncio.sleep(0.01)
    with pytest.raises(SandboxBusy):
        await runner.run(tmp_path / "b.py", tmp_path)
    await first

async def test_run_unavailable_raises_without_calling_podman(tmp_path):
    fake = FakePodman()
    runner = PodmanRunner(cfg(), exec=fake)
    runner.mark_unavailable("self-test failed")
    with pytest.raises(SandboxUnavailable):
        await runner.run(tmp_path / "t.py", tmp_path)
    assert fake.calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_podman_run.py -v`
Expected: FAIL with `ImportError: cannot import name 'SandboxBusy'`

- [ ] **Step 3: Implement `run`, `run_podman`, `SandboxBusy`, `SandboxUnavailable`, `available`, `mark_unavailable(reason: str)`, `mark_available()`**

Slot: `asyncio.Semaphore(config.max_concurrent)` acquired via `asyncio.wait_for(..., config.queue_seconds)`; `asyncio.TimeoutError` → `SandboxBusy`. Elapsed is measured around the `run` call with `time.monotonic()`; if that call raises `asyncio.TimeoutError`, issue `kill <name>` once and pass `timed_out=True` to `classify`. Everything after `run` executes in a `finally` so `rm -f` and `unshare chown` always happen; their failures are logged, not raised. `inspect` output `"<exit> <true|false>"` parses to `(int, bool)`; a non-zero `inspect` return code yields `exit_code=None, oom_killed=False`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_podman_run.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/podman_runner.py server/tests/test_podman_run.py
git commit -m "Supervise sandbox runs with slots, timeout safety net and cleanup"
```

### Task 5: Startup, self-test, image refresh

**Files:**
- Modify: `server/src/app/utility/podman_runner.py`
- Test: `server/tests/test_podman_startup.py`

**Interfaces:**
- Produces: `async PodmanRunner.start(self) -> None` (returns once the readiness/pull/self-test sequence has run; schedules the 60 s pull-retry loop if the image is missing and the 10 min refresh loop); `async PodmanRunner.stop(self) -> None` (cancels loops); `async PodmanRunner.self_test(self) -> str | None` (returns a failure reason or `None`); constructor keyword `sleep: Callable[[float], Awaitable[None]] = asyncio.sleep` for tests.
- Startup podman calls, in order: `info` (retry each second up to 60), `ps -a --filter name=^run- --format {{.Names}}` then `rm -f <each>`, `pull <image>`, then the two self-test runs via `run --rm --entrypoint python3 … --memory=64m <image> -c "bytearray(200*1024*1024)"` and `run --rm --timeout=2 … <image> -c "import time; time.sleep(30)"`, both built with `command()` flags except `--name`, `-v`, `--memory`/`--timeout` overridden as stated.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.utility.sandbox_config import SandboxConfig
from app.utility.podman_runner import PodmanRunner
from tests.test_podman_run import FakePodman, cfg

class ScriptedPodman(FakePodman):
    """Like FakePodman but `run` responses come from a list, consumed in order."""
    def __init__(self, responses=None, run_responses=()):
        super().__init__(responses); self.run_responses = list(run_responses)
    async def __call__(self, *argv, timeout=None):
        if argv[1] == "run":
            self.calls.append(list(argv)); return self.run_responses.pop(0)
        return await super().__call__(*argv, timeout=timeout)

async def no_sleep(_): return None

async def test_start_sequence_and_ready():
    fake = ScriptedPodman({"ps": (0, "run-old\n", "")}, run_responses=[(137, "", "Killed"), (137, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start(); await runner.stop()
    subs = fake.subcommands()
    assert subs[:4] == ["info", "ps", "rm", "pull"] and subs.count("run") == 2
    assert fake.calls[2][:4] == ["podman", "rm", "-f", "run-old"]
    assert runner.available and runner.unavailable_reason is None

async def test_self_test_memory_not_enforced_fails_closed():
    fake = ScriptedPodman(run_responses=[(0, "", ""), (137, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start(); await runner.stop()
    assert not runner.available and "memory" in runner.unavailable_reason

async def test_self_test_timeout_not_enforced_fails_closed():
    fake = ScriptedPodman(run_responses=[(137, "", ""), (0, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start(); await runner.stop()
    assert not runner.available and "timeout" in runner.unavailable_reason

async def test_pull_failure_without_local_image_is_unavailable():
    fake = ScriptedPodman({"pull": (125, "", "manifest unknown"), "image": (1, "", "")})
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start(); await runner.stop()
    assert not runner.available and "image" in runner.unavailable_reason

async def test_pull_failure_with_local_image_continues():
    fake = ScriptedPodman({"pull": (125, "", "offline"), "image": (0, "sha256:abc", "")}, run_responses=[(137, "", ""), (137, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start(); await runner.stop()
    assert runner.available
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_podman_startup.py -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'sleep'`

- [ ] **Step 3: Implement `start`, `stop`, `self_test`, the retry and refresh loops**

Local image presence is `image exists <image>` (exit 0 = present). When the image is unavailable, skip the self-test, `mark_unavailable`, and schedule the 60 s retry loop, which re-runs pull + self-test and calls `mark_available()` on success. Self-test passes when the memory run returns exit 137 *and* the timeout run returns exit 137 or 143. Reasons are `"memory limit not enforced"`, `"timeout not enforced"`, `"sandbox image unavailable: <stderr>"`. Loops are `asyncio.Task`s stored on the instance; `stop()` cancels and awaits them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_podman_startup.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add server/src/app/utility/podman_runner.py server/tests/test_podman_startup.py
git commit -m "Verify sandbox limits at startup and keep the sandbox image fresh"
```

### Task 6: Wire the runner into the routes

**Files:**
- Modify: `server/src/app/routes/tools.py:30-83` (imports, lifespan, `isolate`, `get_temp_dir`), `:266-331` (`run_isolated`)
- Delete: `server/src/app/utility/sandbox.py` (old `IsolationWorkers`/`docker_run`)
- Test: `server/tests/test_tool_routes.py`

**Interfaces:**
- Consumes: `PodmanRunner`, `RunResult`, `Outcome`, `SandboxBusy`, `SandboxUnavailable` (Tasks 2–5).
- Produces: module-level `runner = PodmanRunner(ENVIRONMENT.sandbox)` in `routes/tools.py`; router lifespan calls `await runner.start()` before `yield` and `await runner.stop()` after; `GET /healthz` → `200 {"sandbox": "ready"}` or `503 {"sandbox": "unavailable", "reason": <str>}`; `get_temp_dir` creates directories under `ENVIRONMENT.sandbox.run_dir` (created with `mkdir(parents=True, exist_ok=True)` at startup) with the existing name scheme and mode.
- `run_isolated` response for non-OK outcomes: HTMX → `HTMLResponse(render.render(message + ("\n" + stderr_tail if stderr_tail else "")))`; non-HTMX → `JSONResponse({"detail": message}, 200)`. `SandboxBusy` → `HTTPException(503, "Server busy, try again")`; `SandboxUnavailable` → `HTTPException(503, "Sandbox unavailable")`.

- [ ] **Step 1: Write the failing tests**

Use `fastapi.testclient.TestClient` with the router's `runner` replaced via `monkeypatch`:

```python
import dataclasses, json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.app import app
from app.routes import tools as tools_routes
from app.utility.podman_runner import RunResult, Outcome, SandboxBusy, SandboxUnavailable
from app.models import tools as db

class StubRunner:
    def __init__(self, result=None, raise_=None, available=True):
        self.result, self.raise_, self.available, self.unavailable_reason, self.calls = result, raise_, available, None if available else "self-test failed", []
    async def start(self): pass
    async def stop(self): pass
    async def run(self, tool, run_dir):
        self.calls.append((tool, run_dir))
        if self.raise_: raise self.raise_
        return self.result

@pytest.fixture
def public_tool(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "get_tool_by_id", lambda session, id: db.Tool(id=8, name="byte_converter", code="def byte_converter(): return 1", arguments={}, public=True, tags=[]))
    # SandboxConfig is frozen: swap the whole ENVIRONMENT the routes module sees
    env = tools_routes.ENVIRONMENT
    monkeypatch.setattr(tools_routes, "ENVIRONMENT", dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path)))

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

def test_healthz(monkeypatch):
    assert client(monkeypatch, StubRunner()).get("/healthz").json() == {"sandbox": "ready"}
    r = client(monkeypatch, StubRunner(available=False)).get("/healthz")
    assert r.status_code == 503 and r.json() == {"sandbox": "unavailable", "reason": "self-test failed"}

def test_run_dir_created_under_configured_root(monkeypatch, public_tool, tmp_path):
    stub = StubRunner(RunResult(Outcome.OK, results=None))
    client(monkeypatch, stub).post("/tool/8")
    tool, run_dir = stub.calls[0]
    assert run_dir.parent == tmp_path and tool == run_dir / "byte_converter.py"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_tool_routes.py -v`
Expected: FAIL with `AttributeError: module 'app.routes.tools' has no attribute 'runner'`

- [ ] **Step 3: Rewire `routes/tools.py`, delete `utility/sandbox.py`**

Replace `isolate = sandbox.IsolationWorkers()` with `runner = PodmanRunner(ENVIRONMENT.sandbox)`; `get_temp_dir` and `run_isolated` read `ENVIRONMENT` through the module global at call time (so tests can swap it); in `run_isolated` check `runner.available` first (503) before touching the filesystem, then build the run dir contents as today, call `await runner.run(temp_tool, temp_dir)`, and map the `RunResult` per the Interfaces block. Keep `tool.usage` increment before the run. The lifespan keeps its delete-task cancellation.

- [ ] **Step 4: Run the whole unit suite**

Run: `cd server && python -m pytest -v -m "not integration"`
Expected: all passed (Tasks 1–6)

- [ ] **Step 5: Commit**

```bash
git add server/src/app/routes/tools.py server/tests/test_tool_routes.py
git rm server/src/app/utility/sandbox.py
git commit -m "Run tools through PodmanRunner and expose /healthz"
```

### Task 7: Sandbox image and CI job

**Files:**
- Create: `containers/Containerfile.sandbox`
- Modify: `.github/workflows/main.yml` (rename job `build-and-push` → `app`; add job `sandbox`)
- Modify: `.dockerignore` (replace the `containers/` line with `containers/Containerfile*`)

**Interfaces:**
- Produces: image `raubcamaioni/pywebtools-sandbox` with entrypoint `/venvs/sandbox/bin/sandbox`, `python3` on `PATH` (for the self-test's `--entrypoint python3`).

- [ ] **Step 1: Write `containers/Containerfile.sandbox`**

`FROM python:3.12-slim-bookworm`; apt `libgl1 libxrender1 libglib2.0-0 libgomp1`; `useradd -u 1001 app`; `COPY sandbox /tmp/sandbox`; `python3 -m venv /venvs/sandbox && /venvs/sandbox/bin/pip install --no-cache-dir /tmp/sandbox`; `ENTRYPOINT ["/venvs/sandbox/bin/sandbox"]`.

- [ ] **Step 2: Build and smoke it on the server as `pytools`**

Run (from the repo root, copying the tree as in earlier builds):
`tar --exclude=.git -czf - . | ssh pytools@192.155.89.63 'rm -rf ~/pywebtools/src && mkdir -p ~/pywebtools/src && tar -xzf - -C ~/pywebtools/src && cd ~/pywebtools/src && podman build -q -f containers/Containerfile.sandbox -t pywebtools-sandbox:test . && mkdir -p /tmp/sb && cp tools/lower_case_text.py /tmp/sb/ && echo "{\"input\": {\"__path__\": \"/box/in.txt\"}}" > /tmp/sb/args.json && echo HeLLo > /tmp/sb/in.txt && podman run --rm --network=none -v /tmp/sb:/box pywebtools-sandbox:test --file /box/lower_case_text.py --workdir /box && cat /tmp/sb/result.json'`
Expected: `result.json` printed, containing a path to `output.txt`; `cat /tmp/sb/output.txt` gives `hello`.
(If `args.json`'s path encoding differs, match `app/utility/serializer.JsonEncoder`'s format.)

- [ ] **Step 3: Add the `sandbox` job to the workflow**

Same steps as the `app` job with `images: ${{ secrets.DOCKER_USERNAME }}/pywebtools-sandbox`, `file: ./containers/Containerfile.sandbox`, `cache scope=sandbox`. Jobs run in parallel.

- [ ] **Step 4: Commit and push; confirm both CI jobs pass**

```bash
git add containers/Containerfile.sandbox .github/workflows/main.yml .dockerignore
git commit -m "Build the sandbox runtime image in CI"
git push origin main
```
Check: `curl -s https://api.github.com/repos/RaubCamaioni/PyTools/actions/runs?per_page=1` shows `conclusion: success`; `https://hub.docker.com/v2/repositories/raubcamaioni/pywebtools-sandbox/tags` lists `latest`.

### Task 8: App image (ubi-init, systemd, nested podman)

**Files:**
- Rewrite: `containers/Containerfile.prod`
- Create: `containers/app/user@.service.d-container.conf`, `containers/app/containers.conf.d-nested.conf`, `containers/app/storage.conf`, `containers/app/pywebtools.service`

**Interfaces:**
- Produces: image `raubcamaioni/pywebtools` that boots systemd, starts `user@1000.service`, and runs `pywebtools.service` as user `podman` reading `EnvironmentFile=/run/secrets/pywebtools.env`; listens on 8080.

- [ ] **Step 1: Write the four config files**

`user@.service.d-container.conf`:
```ini
[Service]
Delegate=cpu cpuset io memory pids
PAMName=
Environment=XDG_RUNTIME_DIR=/run/user/%i
```
`containers.conf.d-nested.conf`: `[containers]` / `default_sysctls = []`.
`storage.conf`: `[storage] driver = "overlay"` / `[storage.options.overlay] mount_program = "/usr/bin/fuse-overlayfs"`.
`pywebtools.service` (user unit): `ExecStart=/venvs/server/bin/pywebtool`, `EnvironmentFile=/run/secrets/pywebtools.env`, `Restart=always`, `RestartSec=3`, `WantedBy=default.target`.

- [ ] **Step 2: Rewrite `containers/Containerfile.prod`**

Base `registry.access.redhat.com/ubi9/ubi-init`. `dnf install -y podman fuse-overlayfs shadow-utils python3.12 && dnf clean all`. `useradd -u 1000 -m podman && usermod -p "*" podman`; `/etc/subuid` and `/etc/subgid` = `podman:2000:60000`; linger file; copy the user@ drop-in and enable `user@1000.service` via `multi-user.target.wants` symlink; copy `nested.conf` and `storage.conf` (chown podman); `python3.12 -m venv /venvs/server && /venvs/server/bin/pip install --no-cache-dir /tmp/server`; install the user unit to `/home/podman/.config/systemd/user/` with a `default.target.wants` symlink; `mkdir /data && chown podman:podman /data`; `STOPSIGNAL SIGRTMIN+3`; `EXPOSE 8080`; `CMD ["/sbin/init"]`. Do not touch `newuidmap`'s mode.

- [ ] **Step 3: Build on the server and boot-test with the real secrets, the test database copy and the test sandbox image**

Run as `pytools`: build with `-t pywebtools:nested`, then
`podman run -d --name pwt-nested --device /dev/fuse --security-opt unmask=ALL --memory=3g -v ~/pywebtools/.secrets:/run/secrets/pywebtools.env:ro -v ~/pywebtools/test.db:/data/database.db -v pwt-nested-store:/home/podman/.local/share/containers -p 127.0.0.1:8089:8080 pywebtools:nested`
(first add `SANDBOX_IMAGE=docker.io/raubcamaioni/pywebtools-sandbox:latest` to a *copy* of `.secrets` used for this test, and re-own the copy and `test.db` with `podman unshare chown 1000:1000`).
Expected within ~3 min: `podman exec pwt-nested systemctl is-active user@1000.service` → `active`; `curl -s 127.0.0.1:8089/healthz` → `{"sandbox":"ready"}`; `curl -s -X POST -F input=hi -F output=hexadecimal 127.0.0.1:8089/tool/8` → `"0x68 0x69"`.

- [ ] **Step 4: Commit and push; confirm the `app` CI job passes**

```bash
git add containers/Containerfile.prod containers/app
git commit -m "Run the app as a systemd container with nested rootless podman"
git push origin main
```

### Task 9: Integration tests

**Files:**
- Create: `server/tests/test_integration_sandbox.py`

**Interfaces:**
- Consumes: `PodmanRunner`, `SandboxConfig` with real `run_podman`; skips unless `SANDBOX_INTEGRATION=1`.

- [ ] **Step 1: Write the tests**

Module-level `pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.environ.get("SANDBOX_INTEGRATION") != "1", reason="needs inner podman")]`. Fixture `runner` → `PodmanRunner(SandboxConfig.from_environment(os.environ))` after `await runner.start()`, asserting `runner.available`. Each test writes a tool and `args.json` into a fresh dir under `run_dir` (mode `0o777`, like `get_temp_dir`):

```python
async def test_happy_path_lower_case_text(runner, run_dir): ...  # result is a Path, output.txt == "hello"
async def test_memory_bomb_reports_memory_limit(runner, run_dir): ...  # tool: bytearray(1500*1024*1024); outcome OOM
async def test_infinite_loop_reports_timeout(runner, run_dir): ...  # while True: pass; outcome TIMEOUT, elapsed < 12.5 s
async def test_fork_bomb_hits_pids_limit(runner, run_dir): ...  # 100 subprocess.Popen(["sleep","5"]); outcome CRASHED or result reports error
async def test_network_is_unreachable(runner, run_dir): ...  # socket.create_connection(("1.1.1.1",53)); result contains "unreachable" or OSError text
async def test_sandbox_runs_as_unprivileged_user(runner, run_dir): ...  # tool returns os.getuid() and whether /run/secrets exists; uid == 1001, no secrets visible
async def test_run_dir_owned_by_app_user_after_run(runner, run_dir): ...  # (run_dir/"result.json").stat().st_uid == os.getuid()
```

- [ ] **Step 2: Run them inside the booted test container from Task 8**

Run: `podman exec --user podman -e SANDBOX_INTEGRATION=1 -e XDG_RUNTIME_DIR=/run/user/1000 pwt-nested sh -c 'cd /tmp && tar -xzf /tmp/src.tgz tests && /venvs/server/bin/python -m pytest -m integration tests/test_integration_sandbox.py -v'` (copy the test tree in first with `podman cp`).
Expected: 7 passed.

- [ ] **Step 3: Commit and push**

```bash
git add server/tests/test_integration_sandbox.py
git commit -m "Add integration tests for sandbox limits and isolation"
git push origin main
```

### Task 10: Host rollout

**Files:**
- Modify (on the server, as `pytools`): `~/.config/systemd/user/pywebtools.service`, `~/pywebtools/.secrets`

- [ ] **Step 1: Wait for CI to publish both images, then prepare the host**

```bash
cp ~/.config/systemd/user/pywebtools.service ~/.config/systemd/user/pywebtools.service.pre-nested
sed -i '/^SANDBOX=/d' ~/pywebtools/.secrets
grep -q ^SANDBOX_IMAGE= ~/pywebtools/.secrets || echo 'SANDBOX_IMAGE=docker.io/raubcamaioni/pywebtools-sandbox:latest' >> ~/pywebtools/.secrets
podman unshare chown 1000:1000 ~/pywebtools/.secrets; podman unshare chown -R 1000:1000 ~/pywebtools/data
```

- [ ] **Step 2: Replace the `ExecStart` in `pywebtools.service`**

```
ExecStart=/usr/bin/podman run --rm --name pywebtools \
  --device /dev/fuse --security-opt unmask=ALL \
  --memory=3g --pids-limit=4096 \
  -v %h/pywebtools/.secrets:/run/secrets/pywebtools.env:ro \
  -v %h/pywebtools/data:/data \
  -v pywebtools-inner-store:/home/podman/.local/share/containers \
  -p 172.18.0.1:8080:8080 \
  ${IMAGE}
```
(remove `--userns=keep-id:uid=1001,gid=1001` and `--env-file`). Then `systemctl --user daemon-reload && ~/pywebtools/update.sh && systemctl --user restart pywebtools.service`.

- [ ] **Step 3: Verify**

Run: `podman logs pywebtools 2>&1 | grep -iE "self-test|sandbox|ready" | tail -5`; `curl -s --resolve pywebtools.com:443:192.155.89.63 https://pywebtools.com/healthz`; `curl -s --resolve pywebtools.com:443:192.155.89.63 -X POST -F input=hi -F output=hexadecimal https://pywebtools.com/tool/8`.
Expected: `{"sandbox":"ready"}` and `"0x68 0x69"` (the pre-migration baseline).

- [ ] **Step 4: Rollback path (only if Step 3 fails)**

`cp ~/.config/systemd/user/pywebtools.service.pre-nested ~/.config/systemd/user/pywebtools.service && systemctl --user daemon-reload && podman tag <previous app image id> docker.io/raubcamaioni/pywebtools:latest && systemctl --user restart pywebtools.service`.

- [ ] **Step 5: Update the project memory note and close out**

Record in the memory file that the app now runs the nested design and that `/healthz` exists; remove the "tool execution is BROKEN" line.
