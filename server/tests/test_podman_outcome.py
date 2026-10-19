import json

from app.utility.podman_runner import Outcome, PodmanRunner
from app.utility.sandbox_config import SandboxConfig

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
