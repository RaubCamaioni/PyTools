"""Integration tests for the execution trace: real sandbox, real FIFO.

    SANDBOX_INTEGRATION=1 python -m pytest -m integration tests/test_integration_trace.py -v
"""

import os
import time

import pytest

from app.utility.podman_runner import Outcome, PodmanRunner
from app.utility.sandbox_config import SandboxConfig

from tests.test_integration_sandbox import config, make_run, runner  # noqa: F401  (fixtures)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("SANDBOX_INTEGRATION") != "1", reason="needs the inner podman and the sandbox image"),
]

LOOP_TOOL = """
    def loop_tool() -> int:
        total = 0
        for i in range(3):
            total += i
            total -= 0
        return total
"""

# ten lines of a hot loop: floods the trace for the whole run
FLOOD_TOOL = """
    def flood() -> int:
        n = 0
        while True:
            n += 1
            n -= 1
            n += 2
            n -= 2
            n += 3
            n -= 3
            n += 0
"""


async def test_loop_lines_arrive_in_order_and_run_is_ok(runner, make_run):
    tool, run_dir = make_run("loop_tool", LOOP_TOOL)
    seen = []
    r = await runner.run(tool, run_dir, on_line=seen.append)
    assert r.outcome is Outcome.OK and r.results == 3, r
    assert seen, "no trace events reached the app"
    assert all(1 <= n <= 7 for n in seen)
    assert seen[0] <= 3 and seen[-1] == 7  # starts near the top, ends on the return
    assert 5 in seen or 6 in seen  # loop body lines were reported


async def test_flooding_tool_is_rate_limited_and_times_out(make_run):
    short = SandboxConfig.from_environment({**os.environ, "SANDBOX_TIMEOUT_SECONDS": "5"})
    r = PodmanRunner(short)
    await r.start()
    assert r.available, r.unavailable_reason
    try:
        tool, run_dir = make_run("flood", FLOOD_TOOL)
        seen = []
        started = time.monotonic()
        result = await r.run(tool, run_dir, on_line=seen.append)
        elapsed = time.monotonic() - started
    finally:
        await r.stop()
    assert result.outcome is Outcome.TIMEOUT, result
    assert elapsed < short.timeout_seconds + 3
    assert seen and len(seen) / elapsed <= 60
