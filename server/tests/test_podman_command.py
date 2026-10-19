from pathlib import Path

from app.utility.podman_runner import PodmanRunner
from app.utility.sandbox_config import SandboxConfig

CFG = SandboxConfig.from_environment({})


def test_command_matches_spec_flags():
    r = PodmanRunner(CFG)
    cmd = r.command("run-abc", Path("/tmp/pywebtools-runs/abc/tool.py"), Path("/tmp/pywebtools-runs/abc"))
    assert cmd[:3] == ["podman", "run", "--name"] and cmd[3] == "run-abc"
    # no --userns=auto: a per-sandbox UID mapping would force a re-owned copy of the 2.6 GB
    # sandbox image per mapping on fuse-overlayfs; the sandbox runs as the image's unprivileged user instead
    assert "--userns=auto" not in cmd
    for flag in [
        "--network=none",
        "--uts=host",
        "--user=1001",
        "--cpus=0.5",
        "--memory=1g",
        "--memory-swap=1g",
        "--pids-limit=64",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--timeout=10",
    ]:
        assert flag in cmd
    assert cmd[cmd.index("--tmpfs") + 1] == "/tmp:rw,size=64m"
    # the run directory keeps its own path inside the sandbox: args.json carries absolute upload paths
    # and result.json carries absolute output paths that the app must find on its side afterwards
    assert cmd[cmd.index("-v") + 1] == "/tmp/pywebtools-runs/abc:/tmp/pywebtools-runs/abc:U"
    assert cmd[-5:] == [CFG.image, "--file", "/tmp/pywebtools-runs/abc/tool.py", "--workdir", "/tmp/pywebtools-runs/abc"]
    assert "--rm" not in cmd


def test_command_name_and_volume_with_leading_dash():
    run_dir = Path("/tmp/pywebtools-runs/-_weird")
    name = PodmanRunner.container_name(run_dir)
    assert name == "run--_weird"
    cmd = PodmanRunner(CFG).command(name, run_dir / "t.py", run_dir)
    assert cmd[cmd.index("-v") + 1].startswith("/tmp/pywebtools-runs/-_weird:")
