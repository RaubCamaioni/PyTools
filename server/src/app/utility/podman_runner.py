"""Run uploaded tools in per-run rootless podman containers.

Design: docs/superpowers/specs/2026-10-19-podman-sandbox-runner-design.md
"""

from pathlib import Path
from typing import Awaitable, Callable, Optional

from app.utility.sandbox_config import SandboxConfig

# (argv...) -> (returncode, stdout, stderr); the podman binary is argv[0]
Exec = Callable[..., Awaitable[tuple[int, str, str]]]


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
