import asyncio
import json

import pytest

from app.utility.podman_runner import Outcome, PodmanRunner, SandboxBusy, SandboxUnavailable
from app.utility.sandbox_config import SandboxConfig


class FakePodman:
    """Records argv; `responses` maps subcommand -> (rc, out, err) or an exception."""

    def __init__(self, responses=None, run_delay=0.0):
        self.calls, self.responses, self.run_delay = [], responses or {}, run_delay

    async def __call__(self, *argv, timeout=None):
        self.calls.append(list(argv))
        sub = argv[1]
        if sub == "run":
            # a run longer than the caller's timeout behaves like a hung `podman run`
            if timeout is not None and self.run_delay > timeout:
                raise asyncio.TimeoutError
            await asyncio.sleep(self.run_delay)
        resp = self.responses.get(sub, (0, "", ""))
        if isinstance(resp, Exception):
            raise resp
        return resp

    def subcommands(self):
        return [c[1] for c in self.calls]


def cfg(**kw):
    return SandboxConfig.from_environment({k: str(v) for k, v in kw.items()})


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
