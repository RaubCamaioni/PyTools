"""The app can be served under a URL prefix (ROOT_PATH, uvicorn root_path): every link, asset,
htmx call, redirect and result file link it emits carries that prefix."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.app import app
from app.routes import tools as tools_routes
from app.utility.podman_runner import Outcome, RunResult

from tests.test_auth_routes import FakeGitHub, github  # noqa: F401  (fixture)
from tests.test_tool_routes import StubRunner, public_tool  # noqa: F401  (fixture)

PREFIX = "/tools"


def prefixed_client(monkeypatch, runner=None):
    monkeypatch.setattr(tools_routes, "runner", runner or StubRunner())
    return TestClient(app, root_path=PREFIX)


def unprefixed_urls(page: str) -> list[str]:
    """Site-relative URLs in the page that do not start with the prefix."""
    urls = re.findall(r'(?:href|src|hx-get|hx-post|hx-delete|action)="(/[^"]*)"', page)
    return [u for u in urls if not u.startswith(PREFIX + "/") and u != PREFIX]


def test_home_page_assets_and_links_carry_the_prefix(monkeypatch, public_tool):
    page = prefixed_client(monkeypatch).get(PREFIX + "/").text
    assert unprefixed_urls(page) == []
    assert f'href="{PREFIX}/static/output.css' in page and f'src="{PREFIX}/scripts/htmx.min.js"' in page
    assert f'hx-post="{PREFIX}/tools' in page  # the listing loader
    # the home link is marked active even though the request path is /tools/
    assert re.search(r'href="/tools/" class="[^"]*bg-paper', page)


def test_tool_page_and_result_links_carry_the_prefix(monkeypatch, public_tool):
    c = prefixed_client(monkeypatch, StubRunner(RunResult(Outcome.OK, results={"file": Path("/runs/a/out.png")})))
    page = c.get(PREFIX + "/tool/8").text
    assert unprefixed_urls(page) == []
    assert f'new EventSource("{PREFIX}/trace/"' in page and f"""a[href^="{PREFIX}/download/"]""" in page
    result = c.post(PREFIX + "/tool/8", headers={"HX-Request": "true"}).text
    assert f'href="{PREFIX}/download/runs/a/out.png"' in result
    assert f'src="{PREFIX}/download/runs/a/out.png?preview=1"' in result


def test_login_round_trip_stays_under_the_prefix(monkeypatch, github, public_tool):  # noqa: F811
    import html
    from urllib.parse import parse_qs

    c = prefixed_client(monkeypatch)
    page = c.get(PREFIX + "/").text
    state = parse_qs(html.unescape(page.split("https://github.com/login/oauth/authorize?")[1].split('"')[0]))["state"][0]
    r = c.get(PREFIX + "/auth/github", params={"code": "abc", "state": state}, follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == PREFIX + "/"
    page = c.get(PREFIX + "/").text
    assert f'hx-post="{PREFIX}/logout/button"' in page and unprefixed_urls(page) == []


def test_without_a_prefix_nothing_changes(monkeypatch, public_tool):
    monkeypatch.setattr(tools_routes, "runner", StubRunner())
    page = TestClient(app).get("/").text
    assert 'href="/static/output.css' in page and 'hx-post="/tools' in page
