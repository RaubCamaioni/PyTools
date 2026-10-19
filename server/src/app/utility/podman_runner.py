"""Run uploaded tools in per-run rootless podman containers.

Design: docs/superpowers/specs/2026-10-19-podman-sandbox-runner-design.md
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from app.utility import serializer
from app.utility.sandbox_config import SandboxConfig

logger = logging.getLogger("uvicorn.error")

# (argv..., timeout=None) -> (returncode, stdout, stderr); the podman binary is argv[0]
Exec = Callable[..., Awaitable[tuple[int, str, str]]]

STDERR_TAIL_LINES = 20
# podman kills a timed-out container; a late exit within this margin still counts as the timeout
TIMEOUT_TOLERANCE = 0.5
# the app gives `podman run --timeout` this much extra before killing the container itself
SAFETY_NET_SECONDS = 2.0
READINESS_SECONDS = 60
PULL_RETRY_SECONDS = 60
REFRESH_SECONDS = 600
# startup self-test: a run that must be OOM-killed and a run that must be killed by --timeout
SELFTEST_MEMORY = "64m"
SELFTEST_MEMORY_CODE = "bytearray(200*1024*1024)"
SELFTEST_TIMEOUT = 2
SELFTEST_TIMEOUT_CODE = "import time; time.sleep(30)"
KILLED_EXIT_CODES = (137, 143)


class SandboxBusy(Exception):
    """No sandbox slot became free within the queue wait."""


class SandboxUnavailable(Exception):
    """The sandbox failed its startup checks; tool runs are refused."""


async def run_podman(*argv: str, timeout: Optional[float] = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


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
    def __init__(
        self,
        config: SandboxConfig,
        exec: Optional[Exec] = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.config = config
        self._exec: Exec = exec or run_podman
        self._sleep = sleep
        self._slots = asyncio.Semaphore(config.max_concurrent)
        self._unavailable_reason: Optional[str] = None
        self._tasks: list[asyncio.Task] = []

    # --- startup -----------------------------------------------------------------

    async def start(self):
        """Readiness, leftover cleanup, image pull and the fail-closed self-test."""
        if not await self._wait_ready():
            self.mark_unavailable("inner podman not ready")
        else:
            await self._remove_leftovers()
            await self._prepare()
        self._tasks.append(asyncio.create_task(self._refresh_loop()))
        if not self.available:
            self._tasks.append(asyncio.create_task(self._retry_loop()))

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def self_test(self) -> Optional[str]:
        """Return why limits are not enforced, or None when both checks pass."""
        rc = await self._selftest_run(
            {"--memory": SELFTEST_MEMORY, "--memory-swap": SELFTEST_MEMORY}, SELFTEST_MEMORY_CODE
        )
        if rc not in KILLED_EXIT_CODES:
            return "memory limit not enforced"
        rc = await self._selftest_run({"--timeout": str(SELFTEST_TIMEOUT)}, SELFTEST_TIMEOUT_CODE)
        if rc not in KILLED_EXIT_CODES:
            return "timeout not enforced"
        return None

    async def _selftest_run(self, overrides: dict[str, str], code: str) -> int:
        flags = []
        for flag in self._limit_flags():
            key = flag.split("=")[0]
            flags.append(f"{key}={overrides[key]}" if key in overrides else flag)
        argv = ["podman", "run", "--rm", *flags, "--entrypoint", "python3", self.config.image, "-c", code]
        rc, _, _ = await self._exec(*argv, timeout=SELFTEST_TIMEOUT + 30)
        return rc

    async def _wait_ready(self) -> bool:
        for _ in range(READINESS_SECONDS):
            rc, _, _ = await self._exec("podman", "info")
            if rc == 0:
                return True
            await self._sleep(1)
        return False

    async def _remove_leftovers(self):
        rc, out, _ = await self._exec("podman", "ps", "-a", "--filter", "name=^run-", "--format", "{{.Names}}")
        if rc != 0:
            return
        for name in out.split():
            logger.warning(f"removing leftover sandbox container {name}")
            await self._exec("podman", "rm", "-f", name)

    async def _prepare(self):
        if not await self._ensure_image():
            return
        reason = await self.self_test()
        if reason:
            self.mark_unavailable(reason)
        else:
            self.mark_available()
            logger.info("sandbox self-test passed; sandbox ready")

    async def _ensure_image(self) -> bool:
        image = self.config.image
        rc, _, err = await self._exec("podman", "pull", image)
        if rc == 0:
            return True
        rc, _, _ = await self._exec("podman", "image", "exists", image)
        if rc == 0:
            logger.warning(f"pull of {image} failed ({err.strip()}); using the local copy")
            return True
        self.mark_unavailable(f"sandbox image unavailable: {err.strip()}")
        return False

    async def _retry_loop(self):
        while not self.available:
            await self._sleep(PULL_RETRY_SECONDS)
            try:
                await self._prepare()
            except Exception as e:
                logger.warning(f"sandbox retry failed: {e}")

    async def _refresh_loop(self):
        # sandbox-only releases are picked up without an app restart: new runs use the new local image
        while True:
            await self._sleep(REFRESH_SECONDS)
            try:
                rc, _, err = await self._exec("podman", "pull", self.config.image)
                if rc != 0:
                    logger.warning(f"sandbox image refresh failed: {err.strip()}")
            except Exception as e:
                logger.warning(f"sandbox image refresh raised: {e}")

    # --- one run -----------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._unavailable_reason is None

    @property
    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    def mark_unavailable(self, reason: str):
        logger.error(f"sandbox unavailable: {reason}")
        self._unavailable_reason = reason

    def mark_available(self):
        self._unavailable_reason = None

    async def run(self, tool: Path, run_dir: Path) -> RunResult:
        if not self.available:
            raise SandboxUnavailable(self._unavailable_reason)
        try:
            await asyncio.wait_for(self._slots.acquire(), self.config.queue_seconds)
        except asyncio.TimeoutError:
            raise SandboxBusy()
        try:
            return await self._supervise(tool, run_dir)
        finally:
            self._slots.release()

    async def _supervise(self, tool: Path, run_dir: Path) -> RunResult:
        name = self.container_name(run_dir)
        timed_out = False
        stderr = ""
        started = time.monotonic()
        try:
            try:
                _, _, stderr = await self._exec(
                    *self.command(name, tool, run_dir),
                    timeout=self.config.timeout_seconds + SAFETY_NET_SECONDS,
                )
            except asyncio.TimeoutError:
                timed_out = True
                logger.warning(f"{name}: podman --timeout did not fire, killing container")
                await self._exec("podman", "kill", name)
            elapsed = time.monotonic() - started

            exit_code, oom_killed = await self._inspect(name)
            rc, out, err = await self._exec("podman", "logs", "--tail", str(STDERR_TAIL_LINES), name)
            if not stderr and rc == 0:
                stderr = err or out  # output of a killed run only survives in the container log
            return self.classify(run_dir, exit_code, oom_killed, elapsed, stderr, timed_out)
        finally:
            await self._cleanup(name, run_dir)

    async def _inspect(self, name: str) -> tuple[Optional[int], bool]:
        rc, out, _ = await self._exec(
            "podman", "inspect", "--format", "{{.State.ExitCode}} {{.State.OOMKilled}}", name
        )
        try:
            if rc != 0:
                raise ValueError(out)
            exit_code, oom = out.split()
            return int(exit_code), oom == "true"
        except ValueError:
            logger.warning(f"{name}: could not inspect container state")
            return None, False

    async def _cleanup(self, name: str, run_dir: Path):
        # the sandbox owned its files through --userns=auto; hand them back to the app user
        for argv in (
            ("podman", "rm", "-f", name),
            ("podman", "unshare", "chown", "-R", "0:0", str(run_dir)),
        ):
            try:
                rc, _, err = await self._exec(*argv)
                if rc != 0:
                    logger.warning(f"{' '.join(argv)} failed: {err.strip()}")
            except Exception as e:  # cleanup must never mask the run's result
                logger.warning(f"{' '.join(argv)} raised: {e}")

    @staticmethod
    def container_name(run_dir: Path) -> str:
        # the fixed prefix keeps the name valid even when the directory name starts with - or _
        return f"run-{run_dir.name}"

    def _limit_flags(self) -> list[str]:
        cfg = self.config
        return [
            "--network=none",
            "--uts=host",
            "--userns=auto",
            f"--cpus={cfg.cpus}",
            f"--memory={cfg.memory}",
            f"--memory-swap={cfg.memory}",
            f"--pids-limit={cfg.pids}",
            "--read-only",
            "--tmpfs=/tmp:rw,size=64m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--timeout={int(cfg.timeout_seconds)}",
        ]

    def command(self, name: str, tool: Path, run_dir: Path) -> list[str]:
        flags = self._limit_flags()
        # keep the "--tmpfs <spec>" form the tests and operators expect
        i = flags.index("--tmpfs=/tmp:rw,size=64m")
        flags[i : i + 1] = ["--tmpfs", "/tmp:rw,size=64m"]
        return [
            "podman",
            "run",
            "--name",
            name,
            *flags,
            "-v",
            f"{run_dir}:/box:U",
            self.config.image,
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
