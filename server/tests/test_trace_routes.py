from app.routes import tools as tools_routes
from app.utility.podman_runner import Outcome, RunResult, SandboxBusy

from tests.test_tool_routes import StubRunner, client, public_tool  # noqa: F401  (fixture)

TOKEN = "a" * 32


def events(body: str) -> list[str]:
    return [block for block in body.strip().split("\n\n") if block]


def test_trace_stream_emits_lines_then_end(monkeypatch, public_tool):
    class Runner(StubRunner):
        async def run(self, tool, run_dir, on_line=None):
            on_line(1)
            on_line(2)
            return RunResult(Outcome.OK, results=1)

    c = client(monkeypatch, Runner())
    assert c.post("/tool/8", data={"trace": TOKEN}).status_code == 200
    # the channel outlives the run briefly, so a stream attached afterwards still gets every event
    assert events(c.get("/trace/" + TOKEN).text) == ["event: line\ndata: 1", "event: line\ndata: 2", "event: end\ndata:"]


def test_channel_closed_on_busy(monkeypatch, public_tool):
    c = client(monkeypatch, StubRunner(raise_=SandboxBusy()))
    assert c.post("/tool/8", data={"trace": "b" * 32}).status_code == 503
    assert events(c.get("/trace/" + "b" * 32).text) == ["event: end\ndata:"]


def test_channel_closed_when_tool_missing(monkeypatch, public_tool):
    monkeypatch.setattr(tools_routes.db_tools, "get_tool_by_id", lambda session, id: None)
    c = client(monkeypatch, StubRunner())
    assert c.post("/tool/8", data={"trace": "e" * 32}).status_code == 404
    assert events(c.get("/trace/" + "e" * 32).text) == ["event: end\ndata:"]


def test_unknown_token_ends_after_wait(monkeypatch):
    monkeypatch.setattr(tools_routes, "TRACE_WAIT_SECONDS", 0.05)
    r = client(monkeypatch, StubRunner()).get("/trace/" + "c" * 32)
    assert r.headers["content-type"].startswith("text/event-stream")
    assert events(r.text) == ["event: end\ndata:"]


def test_malformed_token_is_404(monkeypatch):
    assert client(monkeypatch, StubRunner()).get("/trace/short").status_code == 404
    assert client(monkeypatch, StubRunner()).get("/trace/" + "." * 32).status_code == 404


def test_token_reuse_replaces_channel():
    reg = tools_routes.TRACES
    a = reg.register("d" * 32)
    b = reg.register("d" * 32)
    assert a.closed and not b.closed


def test_bad_token_is_ignored(monkeypatch, public_tool):
    stub = StubRunner(RunResult(Outcome.OK, results=1))
    assert client(monkeypatch, stub).post("/tool/8", data={"trace": "../x"}).status_code == 200
    assert stub.on_line is None  # no channel, no trace


def test_good_token_gives_runner_a_callback(monkeypatch, public_tool):
    stub = StubRunner(RunResult(Outcome.OK, results=1))
    client(monkeypatch, stub).post("/tool/8", data={"trace": "f" * 32})
    assert stub.on_line is not None
