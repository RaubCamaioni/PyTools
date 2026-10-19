"""Run uploaded tools in per-run rootless podman containers.

Design: docs/superpowers/specs/2026-10-19-podman-sandbox-runner-design.md
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from app.utility import serializer
from app.utility.sandbox_config import SandboxConfig

# (argv...) -> (returncode, stdout, stderr); the podman binary is argv[0]
Exec = Callable[..., Awaitable[tuple[int, str, str]]]

STDERR_TAIL_LINES = 20
# podman kills a timed-out container; a late exit within this margin still counts as the timeout
TIMEOUT_TOLERANCE = 0.5


class Outcome(Enum):
    OK = auto()
    TIMEOUT = auto()
    OOM = auto()
    CRASHED = auto()


@dataclass
class RunResult:
    outcome: Outcome
    results: Any = None  # deserialized result.json when outcome is OK
    message: Optional[str] = None  # user-facing text for every other outcome
    stderr_tail: str = ""


class PodmanRunner:
    def __init__(self, config: SandboxConfig, exec: Optional[Exec] = None):
        self.config = config
        self._exec = exec

    @staticmethod
    def container_name(run_dir: Path) -> str:
        # the fixed prefix keeps the name valid even when the directory name starts with - or _
        return f"run-{run_dir.name}"

    def command(self, name: str, tool: Path, run_dir: Path) -> list[str]:
        cfg = self.config
        return [
            "podman",
            "run",
            "--name",
            name,
            "--network=none",
            "--uts=host",
            "--userns=auto",
            f"--cpus={cfg.cpus}",
            f"--memory={cfg.memory}",
            f"--memory-swap={cfg.memory}",
            f"--pids-limit={cfg.pids}",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,size=64m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--timeout={int(cfg.timeout_seconds)}",
            "-v",
            f"{run_dir}:/box:U",
            cfg.image,
            "--file",
            f"/box/{tool.name}",
            "--workdir",
            "/box",
        ]

    def classify(
        self,
        run_dir: Path,
        exit_code: Optional[int],
        oom_killed: bool,
        elapsed: float,
        stderr: str,
        timed_out: bool = False,
    ) -> RunResult:
        cfg = self.config
        tail = "\n".join(stderr.splitlines()[-STDERR_TAIL_LINES:])

        results_file = run_dir / "result.json"
        if results_file.exists():
            try:
                with open(results_file, "r") as f:
                    return RunResult(Outcome.OK, results=serializer.load(f), stderr_tail=tail)
            except ValueError:
                pass  # unreadable result: treated as a crash below

        if oom_killed:
            return RunResult(Outcome.OOM, message=f"Tool exceeded the {cfg.memory_label} memory limit", stderr_tail=tail)
        if timed_out or elapsed >= cfg.timeout_seconds - TIMEOUT_TOLERANCE:
            return RunResult(Outcome.TIMEOUT, message=f"Tool exceeded the {cfg.timeout_seconds:g} second limit", stderr_tail=tail)
        return RunResult(Outcome.CRASHED, message="Tool failed to run", stderr_tail=tail)
