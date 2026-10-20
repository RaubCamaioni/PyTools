import re

from app.utility import render


def test_list_items_loader_requests_a_full_next_page():
    tools = [(i, f"tool{i}") for i in range(50)]
    html = render.list_items("", tools, end=50, tags=[], page=50)
    # the infinite-scroll loader must fetch the next 50, not one tool at a time
    assert re.search(r'hx-post="/tools\?start=50&(amp;)?end=100"', html), html[-300:]


def test_list_items_without_more_pages_has_no_loader():
    html = render.list_items("", [(1, "a")], end=None, tags=[])
    assert "hx-post" not in html
