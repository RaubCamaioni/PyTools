"""The session cookie says who is logged in and nothing else. The role and the ban are read from the database on
every request, so removing an admin role or banning an account reaches the sessions that already exist."""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from app import ENVIRONMENT
from app.app import app
from app.models import tools as db
from app.routes import auth as auth_routes

from tests.test_auth_routes import FakeGitHub, state_for
from tests.test_metadata_routes import post, set_user, stored
from tests.test_tool_routes import StubRunner

GITHUB_ID = 880011
ME = db.hash_id(f"github:{GITHUB_ID}")
SOMEONE = 880022  # an account that never logs in
CLEAN = {"admin": False, "banned": False, "banned_until": None}


@pytest.fixture
def login(monkeypatch):
    """login(**fields) sets the account's row, logs in through the real route and returns the client: the
    session a test keeps using while the row changes underneath it."""
    monkeypatch.setattr(auth_routes, "github", FakeGitHub({"id": GITHUB_ID, "login": "mallory"}))

    def login(**fields):
        set_user(ME, **{**CLEAN, **fields})
        c = TestClient(app)
        r = c.get("/auth/github", params={"code": "abc", "state": state_for(c)}, follow_redirects=False)
        assert r.status_code in (302, 307)
        return c

    yield login
    set_user(ME, **CLEAN)


def someone_elses_tool(name, public):
    with db.Session(db.engine) as session:
        db.get_user(session, SOMEONE)
        tool = db.Tool(name=name, code="", user_id=SOMEONE, public=public)
        session.add(tool)
        session.commit()
        return tool.id


def tool_row(tool_id):
    with db.Session(db.engine) as session:
        return session.get(db.Tool, tool_id)


def session_data(c):
    return json.loads(base64.b64decode(c.cookies["pytools_session"].strip('"').split(".")[0]))


def test_the_cookie_holds_only_the_user_id(login):
    assert session_data(login(admin=True)) == {"user_id": ME}


def test_a_removed_admin_role_reaches_an_existing_session(login):
    c = login(admin=True)
    assert c.post(f"/admin/ban/{SOMEONE + 1}", params={"months": "1"}).status_code == 200
    assert "ls -l /home/*/tools/" in c.get("/user").text
    set_user(ME, admin=False)
    assert c.post(f"/admin/ban/{SOMEONE + 1}", params={"months": "1"}).status_code == 404
    assert c.post(f"/admin/unban/{SOMEONE + 1}").status_code == 404
    assert "ls -l /home/*/tools/" not in c.get("/user").text


def test_a_former_admin_cannot_open_or_delete_another_users_tool(login):
    tool_id = someone_elses_tool("not_yours_private", public=False)
    c = login(admin=True)
    assert c.post(f"/tool/{tool_id}/vote", params={"direction": "up"}).status_code == 200  # an admin sees it
    set_user(ME, admin=False)
    assert c.post(f"/tool/{tool_id}/vote", params={"direction": "up"}).status_code == 404
    assert c.post(f"/tool/{tool_id}/report", data={"reason": "x"}).status_code == 404
    assert c.delete(f"/manage/tool/delete/{tool_id}").status_code == 404
    assert tool_row(tool_id) is not None


def test_a_ban_reaches_an_existing_session(monkeypatch, login):
    public_id = someone_elses_tool("votable", public=True)
    c = login()
    assert post(c, monkeypatch, StubRunner(), "banned_later").status_code == 200
    tool_id, _ = stored("banned_later")
    assert c.get("/whoami").json()["id"] == ME
    alias = c.get("/whoami").json()["alias"]

    set_user(ME, banned=True, banned_until=datetime.now(timezone.utc) + timedelta(days=30))
    assert c.post(f"/manage/tool/settings/{tool_id}", params={"public": "true"}).status_code == 404
    assert tool_row(tool_id).public is False
    assert c.post("/manage/user/settings", data={"alias": "still-here"}).status_code == 404
    assert c.get("/whoami").status_code == 401
    assert "[login to vote]" in c.post(f"/tool/{public_id}/vote", params={"direction": "up"}).text
    assert "banned_later" not in c.post("/user/tools").text
    assert c.delete(f"/manage/tool/delete/{tool_id}").status_code != 200 and tool_row(tool_id) is not None
    page = c.get("/user").text
    assert "anonymous@pytools" in page and "[login]" in page

    # the ban's period passes: the same session works again
    set_user(ME, banned=True, banned_until=datetime.now(timezone.utc) - timedelta(days=1))
    assert c.get("/whoami").json() == {"id": ME, "alias": alias}
    assert c.post(f"/manage/tool/settings/{tool_id}", params={"public": "true"}).status_code == 200
    assert tool_row(tool_id).public is True


def test_an_alias_change_shows_on_the_next_page(login):
    c = login()
    try:
        assert c.post("/manage/user/settings", data={"alias": "renamed"}).status_code == 200
        assert "renamed@pytools" in c.get("/").text and c.get("/whoami").json()["alias"] == "renamed"
    finally:
        set_user(ME, alias="mallory")


def test_a_cookie_that_carries_a_user_record_is_not_a_login(login):
    # the cookie format before this one: the whole record, with its role, was signed into the cookie
    login()
    record = db.User(id=ME, alias="mallory", admin=True).model_dump_json()
    payload = base64.b64encode(json.dumps({"user": record}).encode())
    c = TestClient(app)
    c.cookies.set("pytools_session", TimestampSigner(ENVIRONMENT.SESSION_KEY).sign(payload).decode())
    assert c.post(f"/admin/ban/{SOMEONE + 1}", params={"months": "1"}).status_code == 404
    assert c.get("/whoami").status_code == 401
