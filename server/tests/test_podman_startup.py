from app.utility.podman_runner import PodmanRunner
from tests.test_podman_run import FakePodman, cfg


class ScriptedPodman(FakePodman):
    """Like FakePodman but `run` responses come from a list, consumed in order."""

    def __init__(self, responses=None, run_responses=()):
        super().__init__(responses)
        self.run_responses = list(run_responses)

    async def __call__(self, *argv, timeout=None):
        if argv[1] == "run":
            self.calls.append(list(argv))
            return self.run_responses.pop(0)
        return await super().__call__(*argv, timeout=timeout)


async def no_sleep(_):
    return None


async def test_start_sequence_and_ready():
    fake = ScriptedPodman({"ps": (0, "run-old\n", "")}, run_responses=[(137, "", "Killed"), (137, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    subs = fake.subcommands()
    assert subs[:4] == ["info", "ps", "rm", "pull"] and subs.count("run") == 2
    assert fake.calls[2][:4] == ["podman", "rm", "-f", "run-old"]
    assert runner.available and runner.unavailable_reason is None


async def test_self_test_accepts_podman_timeout_exit_code():
    # podman reports a --timeout kill as exit 255 (inspect ExitCode -1), not 137
    fake = ScriptedPodman(run_responses=[(137, "", ""), (255, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert runner.available


async def test_self_test_memory_not_enforced_fails_closed():
    fake = ScriptedPodman(run_responses=[(0, "", ""), (137, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert not runner.available and "memory" in runner.unavailable_reason


async def test_self_test_timeout_not_enforced_fails_closed():
    fake = ScriptedPodman(run_responses=[(137, "", ""), (0, "", "")])
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert not runner.available and "timeout" in runner.unavailable_reason


async def test_pull_failure_without_local_image_is_unavailable():
    fake = ScriptedPodman({"pull": (125, "", "manifest unknown"), "image": (1, "", "")})
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert not runner.available and "image" in runner.unavailable_reason


async def test_start_without_podman_binary_is_unavailable():
    async def no_podman(*argv, timeout=None):
        raise FileNotFoundError("podman")

    runner = PodmanRunner(cfg(), exec=no_podman, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert not runner.available and "not ready" in runner.unavailable_reason


async def test_pull_failure_with_local_image_continues():
    fake = ScriptedPodman(
        {"pull": (125, "", "offline"), "image": (0, "sha256:abc", "")},
        run_responses=[(137, "", ""), (137, "", "")],
    )
    runner = PodmanRunner(cfg(), exec=fake, sleep=no_sleep)
    await runner.start()
    await runner.stop()
    assert runner.available
