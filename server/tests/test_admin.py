import json

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.app import app
from app.models import tools as db
from app.routes import tools as tools_routes

from tests.test_tool_routes import StubRunner, client


def engine_with(tools=(), users=()):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for u in users:
            session.add(u)
        for t in tools:
            session.add(t)
        session.commit()
    return engine


def test_migration_adds_role_columns_once():
    # a database from before roles existed: user(id, alias) only
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE user (id INTEGER PRIMARY KEY, alias VARCHAR NOT NULL)"))
        conn.execute(text("INSERT INTO user (id, alias) VALUES (1, 'rob')"))
    db.migrate(engine)
    db.migrate(engine)  # idempotent
    columns = {c["name"] for c in inspect(engine).get_columns("user")}
    assert {"admin", "banned"} <= columns
    with engine.connect() as conn:
        assert conn.execute(text("SELECT admin, banned FROM user WHERE id = 1")).one() == (0, 0)


def test_users_with_tools_lists_every_account_and_its_tools():
    engine = engine_with(
        users=[db.User(id=1, alias="rob", admin=True), db.User(id=2, alias="eve")],
        tools=[
            db.Tool(name="a", code="", user_id=1, public=True, tags=[]),
            db.Tool(name="b", code="", user_id=2, public=False, tags=[]),
            db.Tool(name="c", code="", user_id=2, public=True, tags=[]),
        ],
    )
    with Session(engine) as session:
        listing = db.get_users_with_tools(session)
    assert [(u.id, u.alias, [t.name for t in ts]) for u, ts in listing] == [(1, "rob", ["a"]), (2, "eve", ["b", "c"])]


def test_ban_unpublishes_the_users_tools_and_unban_keeps_them_private():
    engine = engine_with(
        users=[db.User(id=2, alias="eve")],
        tools=[db.Tool(name="c", code="", user_id=2, public=True, tags=[])],
    )
    with Session(engine) as session:
        db.set_banned(session, 2, True)
        assert session.get(db.User, 2).banned and not session.exec(db.select(db.Tool)).one().public
        db.set_banned(session, 2, False)
        assert not session.get(db.User, 2).banned and not session.exec(db.select(db.Tool)).one().public


def test_admin_page_is_404_for_anonymous_and_ordinary_users(monkeypatch):
    from app.routes import admin as admin_routes

    c = client(monkeypatch, StubRunner())
    assert c.get("/admin").status_code == 404
    monkeypatch.setattr(admin_routes, "session_user", lambda request: db.User(id=2, alias="eve"))
    assert c.get("/admin").status_code == 404
    assert c.post("/admin/ban/2", params={"banned": "true"}).status_code == 404


def test_admin_page_lists_accounts_and_their_tools(monkeypatch):
    from app.routes import admin as admin_routes

    monkeypatch.setattr(admin_routes, "session_user", lambda request: db.User(id=1, alias="rob", admin=True))
    monkeypatch.setattr(
        db,
        "get_users_with_tools",
        lambda session: [
            (db.User(id=1, alias="rob", admin=True), [db.Tool(id=5, name="a", code="", user_id=1, public=True, tags=[])]),
            (db.User(id=2, alias="eve", banned=True), [db.Tool(id=6, name="b", code="", user_id=2, public=False, tags=[])]),
        ],
    )
    page = client(monkeypatch, StubRunner()).get("/admin").text
    assert "ls -l /home/*/tools/ | column -t" in page
    assert page.index("rob/ ") < page.index("a.py") < page.index("eve/ ") < page.index("b.py")
    assert 'href="/tool/6"' in page  # private tools are linked for the admin
    assert "[banned]" in page and "[ban]" in page  # eve's state inverted, rob's switch off


def test_admin_can_ban_and_unban(monkeypatch):
    from app.routes import admin as admin_routes

    calls = []
    monkeypatch.setattr(admin_routes, "session_user", lambda request: db.User(id=1, alias="rob", admin=True))
    monkeypatch.setattr(db, "set_banned", lambda session, user_id, banned: calls.append((user_id, banned)))
    c = client(monkeypatch, StubRunner())
    assert c.post("/admin/ban/2", params={"banned": "true"}).status_code == 200
    assert c.post("/admin/ban/2", params={"banned": "false"}).status_code == 200
    assert c.post("/admin/ban/1", params={"banned": "true"}).status_code == 400  # not yourself
    assert calls == [(2, True), (2, False)]


def test_admin_opens_a_private_tool_page(monkeypatch, tmp_path):
    import dataclasses

    monkeypatch.setattr(
        tools_routes.db_tools,
        "get_tool_by_id",
        lambda session, id: db.Tool(id=9, name="secret", code="def secret(): return 1", arguments={}, public=False, user_id=2, tags=[]),
    )
    env = tools_routes.ENVIRONMENT
    monkeypatch.setattr(tools_routes, "ENVIRONMENT", dataclasses.replace(env, sandbox=dataclasses.replace(env.sandbox, run_dir=tmp_path)))
    c = client(monkeypatch, StubRunner())
    assert c.get("/tool/9").status_code == 404  # anonymous
    monkeypatch.setattr(tools_routes, "session_user", lambda request: db.User(id=1, alias="rob", admin=True))
    assert c.get("/tool/9").status_code == 200


def test_banned_user_cannot_log_in(monkeypatch):
    from app.routes import auth as auth_routes

    class FakeGitHub:
        configured = True

        def login_url(self, state):
            return "https://github.example/authorize?state=" + state

        async def user_for_code(self, code):
            return {"login": "eve", "id": 7}

    monkeypatch.setattr(auth_routes, "github", FakeGitHub())
    monkeypatch.setattr(auth_routes, "get_user", lambda session, id: db.User(id=2, alias="eve", banned=True))
    c = TestClient(app)
    # plant a matching state the way the login button does
    c.get("/login/button")
    monkeypatch.setattr(auth_routes.secrets, "compare_digest", lambda a, b: True)
    r = c.get("/auth/github", params={"code": "x", "state": "y"}, follow_redirects=False)
    assert r.status_code == 403 and "banned" in r.json()["detail"]


def test_session_user_json_carries_admin_flag():
    user = db.User(id=1, alias="rob", admin=True)
    assert json.loads(user.model_dump_json())["admin"] is True
