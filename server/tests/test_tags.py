import html

from sqlmodel import Session, SQLModel, create_engine

from app.models import tools as db
from app.routes import tools as tools_routes

from tests.test_tool_routes import StubRunner, client


def session_with(tools):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    for t in tools:
        session.add(t)
    session.commit()
    return session


def test_get_tag_counts_counts_public_tags_without_tool_names():
    session = session_with(
        [
            db.Tool(name="pdf_merge", code="", tags=["pdf", "Merge", "pdf_merge"], public=True, user_id=1),
            db.Tool(name="pdf_split", code="", tags=["pdf", "split", "pdf_split"], public=True, user_id=1),
            db.Tool(name="secret", code="", tags=["pdf", "hidden", "secret"], public=False, user_id=1),
        ]
    )
    counts = db.get_tag_counts(session)
    assert counts == [("pdf", 2), ("merge", 1), ("split", 1)]  # by count, then name; private tools excluded


def test_home_page_lists_tags_as_a_first_line_grep(monkeypatch):
    monkeypatch.setattr(db, "get_tag_counts", lambda session: [("converter", 55), ("pdf", 12), ("ring", 1), ("zip", 1)])
    page = client(monkeypatch, StubRunner()).get("/").text
    assert "head -n1 tools/*.py | grep -i" in page
    assert page.index('value="converter"') < page.index('value="pdf"') < page.index('value="ring"')
    assert "[+2 more]" in page and "[-2 less]" in page  # single-use tags fold; the toggle mirrors as -N less


def test_tools_route_filters_by_selected_tags(monkeypatch):
    calls = []

    def fake(session, tags, start, end):
        calls.append(tags)
        return [(i, f"pdf_tool{i}") for i in range(50)]  # a full page: the loader for the next one follows

    monkeypatch.setattr(db, "get_tools_by_tags", fake)
    r = client(monkeypatch, StubRunner()).post("/tools?start=0&end=50", data={"search": "merge", "tag": ["pdf", "text"]})
    assert r.status_code == 200 and calls == [["merge", "pdf", "text"]]
    # the infinite-scroll loader carries every term forward
    assert 'hx-vals=\'{"search": "merge pdf text" }\'' in html.unescape(r.text) or "merge pdf text" in r.text


def test_get_tag_counts_narrows_to_tools_matching_the_terms():
    session = session_with(
        [
            db.Tool(name="pdf_merge", code="", tags=["pdf", "merge", "pdf_merge"], public=True, user_id=1),
            db.Tool(name="pdf_split", code="", tags=["pdf", "split", "pdf_split"], public=True, user_id=1),
            db.Tool(name="image_crop", code="", tags=["image", "crop", "image_crop"], public=True, user_id=1),
        ]
    )
    assert db.get_tag_counts(session, ["pdf"]) == [("pdf", 2), ("merge", 1), ("split", 1)]
    assert db.get_tag_counts(session, ["pdf", "split"]) == [("pdf", 1), ("split", 1)]


def test_tools_route_swaps_in_the_overlapping_tags(monkeypatch):
    seen = []

    def counts(session, terms=()):
        seen.append(list(terms))
        return [("pdf", 2), ("merge", 1), ("split", 1)]

    monkeypatch.setattr(db, "get_tag_counts", counts)
    monkeypatch.setattr(db, "get_tools_by_tags", lambda session, tags, start, end: [(1, "pdf_merge")])
    r = client(monkeypatch, StubRunner()).post("/tools?start=0&end=50", data={"tag": ["pdf"]})
    assert r.status_code == 200 and seen == [["pdf"]]
    body = html.unescape(r.text)
    assert 'id="tag-filters"' in body and 'hx-swap-oob="true"' in body
    assert 'value="pdf" checked' in body and 'value="merge"' in body and "more]" not in body  # no fold while filtering


def test_scrolling_pages_do_not_swap_the_tags(monkeypatch):
    monkeypatch.setattr(db, "get_tag_counts", lambda session, terms=(): [("pdf", 2)])
    monkeypatch.setattr(db, "get_tools_by_tags", lambda session, tags, start, end: [(1, "pdf_merge")])
    r = client(monkeypatch, StubRunner()).post("/tools?start=50&end=100", data={"tag": ["pdf"]})
    assert 'id="tag-filters"' not in r.text


def test_home_page_search_field_takes_any_typing(monkeypatch):
    from app.app import app
    from fastapi.testclient import TestClient

    page = TestClient(app).get("/").text
    assert "autofocus" in page.split('name="search"')[1].split(">")[0]  # focused on load
    assert 'document.addEventListener("keydown"' in page and "search.focus()" in page  # and on any key
