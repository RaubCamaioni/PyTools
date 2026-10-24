"""Browsing by category: /c/<category> and /c/<category>/<subcategory> list the public tools filed there
(extras included, unfiled ones under Miscellaneous), and the front page shows the tree with counts."""

import html
import re

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.metadata.categories import Categories
from app.models import tools as db
from app.routes import browse
from app.routes import tools as tools_routes
from sandboxcore.host import Sandbox

from tests.test_tool_routes import StubRunner


@pytest.fixture(scope="module")
def filed():
    """br_a: home/kitchen + workshop/tool-storage; br_b: home/bathroom; br_c: private, home/kitchen; br_d: none."""
    ids = {}
    with db.Session(db.engine) as session:
        for name, paths, public in [
            ("br_a", ["home/kitchen", "workshop/tool-storage"], True),
            ("br_b", ["home/bathroom"], True),
            ("br_c", ["home/kitchen"], False),
            ("br_d", None, True),
        ]:
            tool = db.Tool(name=name, code="", user_id=1, public=public)
            session.add(tool)
            session.commit()
            if paths is not None:
                Categories().save(session, tool.id, paths)
                session.commit()
            ids[name] = tool.id
    return ids


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(tools_routes, "sandbox", Sandbox(tools_routes.ENVIRONMENT.sandbox, runner=StubRunner()))
    return TestClient(app)


def listed(client, category=None, search=""):
    """The br_* names the infinite list shows for a category (other tests share this database)."""
    data = {"search": search, **({"category": category} if category is not None else {})}
    page = client.post("/tools?start=0&end=500", data=data).text
    return {name for name in re.findall(r'>([^<>]+)\.py</span>', page) if name.startswith("br_")}


def test_category_lists(client, filed):
    assert listed(client, "home") == {"br_a", "br_b"}
    assert listed(client, "home/kitchen") == {"br_a"}  # br_c is private
    assert listed(client, "workshop/tool-storage") == {"br_a"}  # filed there as an extra
    assert listed(client, "misc") == {"br_d"}
    assert listed(client, "home/kitchen", search="br_") == {"br_a"}  # search within the category
    assert listed(client, "nope") == set()
    assert listed(client) >= {"br_a", "br_b", "br_d"}


def test_category_pages_exist_only_for_the_tree(client, filed):
    assert client.get("/c/home").status_code == 200 and client.get("/c/home/kitchen").status_code == 200
    assert client.get("/c/misc").status_code == 200
    for missing in ["/c/nope", "/c/home/nope", "/c/misc/x", "/c/home/kitchen/x"]:
        assert client.get(missing).status_code == 404, missing


def test_category_page_has_breadcrumb_description_and_scoped_list(client, filed):
    page = client.get("/c/home/kitchen").text
    assert 'href="/c/home"' in page and ">Kitchen<" in page
    assert "Cooking, baking, food storage and serving." in page
    assert '<input type="hidden" name="category" value="home/kitchen">' in page  # the search stays inside
    assert '"category": "home/kitchen"' in page  # and so does the infinite list's loader


def test_counts_ignore_private_tools(filed):
    with db.Session(db.engine) as session:
        counts = browse.category_counts(session)
    with db.Session(db.engine) as session:  # counts include other tests' public tools: compare with the list
        kitchen = db.search_tools(session, [], 0, 10_000, category="home/kitchen")
    assert counts["home/kitchen"] == len(kitchen)
    assert filed["br_c"] not in {row[0] for row in kitchen}
    assert counts["home"] >= 2 and counts["misc"] >= 1


def test_index_shows_the_bar_in_yaml_order(client, filed):
    page = client.get("/").text
    bar = page.split('id="category-bar"')[1].split("</nav>")[0]
    names = re.findall(r'<summary[^>]*>([^<(]+)', bar)
    order = ["Converters", "Text", "Developer", "Security", "Utilities", "Home", "Office & Desk", "Workshop",
             "Hardware & Electronics", "Outdoor & Garage", "Hobbies"]
    shown = [html.unescape(n).strip() for n in names]
    assert "Home" in shown and "Workshop" in shown  # br_a and br_b are filed there
    assert shown == [n for n in order if n in shown]  # in the tree's order
    assert 'href="/c/home/kitchen"' in bar and 'href="/c/misc"' in bar


def test_index_takes_a_search_from_the_url(client, filed):
    page = client.get("/", params={"search": "kitchen"}).text
    assert 'value="kitchen"' in page.split('name="search"')[1].split(">")[0]
    assert '"search": "kitchen"' in page  # the first page of the list is filtered too


def test_search_from_the_url_cannot_break_the_loader(client, filed):
    page = client.get("/", params={"search": "\"}' x=\"<b>"}).text
    loader = page.split('hx-trigger="revealed"')[1].split(">")[0]
    assert "<b>" not in page.split('id="tool-list"')[1].split("</ul>")[0]
    assert "x=" not in loader.split("hx-vals=")[0]


def test_cleared_categories_fall_back_to_misc(client, filed):
    with db.Session(db.engine) as session:
        tool = db.Tool(name="br_cleared", code="", user_id=1, public=True)
        session.add(tool)
        session.commit()
        Categories().save(session, tool.id, ["home/kitchen"])
        session.commit()
        Categories().save(session, tool.id, [])  # the owner removed every category
        session.commit()
    assert "br_cleared" in listed(client, "misc") and "br_cleared" not in listed(client, "home")


# --- the kind view: ?kind=model -----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def kinds():
    """kd_model (a model in home/kitchen with a thumbnail) and kd_script (a script in text/formatting)."""
    ids = {}
    with db.Session(db.engine) as session:
        for name, kind, path in [("kd_model", "model", "home/kitchen"), ("kd_script", "script", "text/formatting")]:
            tool = db.Tool(name=name, code="", user_id=1, public=True, kind=kind,
                           preview_svg="<svg/>" if kind == "model" else "")
            session.add(tool)
            session.commit()
            Categories().save(session, tool.id, [path])
            session.commit()
            ids[name] = tool.id
    return ids


def test_the_model_view_lists_only_models_as_cards(client, kinds):
    page = client.post("/tools?start=0&end=500", data={"search": "kd_", "kind": "model"}).text
    assert f'href="/tool/{kinds["kd_model"]}"' in page and f'href="/tool/{kinds["kd_script"]}"' not in page
    assert '<li class="card">' in page and f'src="/tool/{kinds["kd_model"]}/preview.svg"' in page


def test_the_all_view_lists_both_with_a_thumbnail_on_models_only(client, kinds):
    page = client.post("/tools?start=0&end=500", data={"search": "kd_"}).text
    model_row = page.split(f'href="/tool/{kinds["kd_model"]}"')[0].rsplit("<li", 1)[1] + page.split(f'href="/tool/{kinds["kd_model"]}"')[1].split("</li>")[0]
    script_row = page.split(f'href="/tool/{kinds["kd_script"]}"')[1].split("</li>")[0]
    assert "preview.svg" in model_row and "preview.svg" not in script_row and '<li class="card">' not in page


def test_the_model_view_keeps_kind_in_every_link(client, kinds):
    page = client.get("/", params={"kind": "model"}).text
    bar = page.split('id="category-bar"')[1].split("</nav>")[0]
    links = re.findall(r'href="(/c/[^"]*)"', bar)
    assert links and all(link.endswith("?kind=model") for link in links)
    assert '<input type="hidden" name="kind" value="model">' in page  # the search keeps it
    loader = page.split('hx-trigger="revealed"')[1].split(">")[0]
    assert '"kind": "model"' in html.unescape(loader)  # and so does the infinite list
    assert 'href="/?kind=model"' in page and 'href="/"' in page  # the [all] [models] switch
    sub = client.get("/c/home/kitchen", params={"kind": "model"}).text
    assert '<input type="hidden" name="kind" value="model">' in sub and 'href="/c/home?kind=model"' in sub


def test_counts_and_the_bar_follow_the_view(client, kinds):
    with db.Session(db.engine) as session:
        models, everything = browse.category_counts(session, "model"), browse.category_counts(session)
    assert models["text"] == 0 and everything["text"] >= 1 and models["home"] >= 1
    model_bar = client.get("/", params={"kind": "model"}).text.split('id="category-bar"')[1].split("</nav>")[0]
    all_bar = client.get("/").text.split('id="category-bar"')[1].split("</nav>")[0]
    assert ">Text <" not in model_bar and ">Text <" in all_bar  # no models in Text: hidden in the model view
    assert ">Home <" in model_bar


@pytest.mark.parametrize("junk", ["MODEL", "<b>x</b>", "", "script", "models"])
def test_an_unknown_kind_is_the_all_view(client, kinds, junk):
    r = client.get("/", params={"kind": junk})
    assert r.status_code == 200 and "<b>x</b>" not in r.text
    assert '<input type="hidden" name="kind"' not in r.text
    r = client.post("/tools?start=0&end=500", data={"search": "kd_", "kind": junk})
    assert r.status_code == 200 and f'href="/tool/{kinds["kd_script"]}"' in r.text
