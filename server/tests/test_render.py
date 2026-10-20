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


def test_render_dict_is_block_formatted_with_closing_brace_on_its_own_line():
    html = render.render({"scientific": "6.022e23", "exponent": 23, "nested": {"a": [1, 2]}})
    text = html.replace("<br>", "\n")
    assert text == (
        "<pre>{\n"
        "    'scientific': '6.022e23',\n"
        "    'exponent': 23,\n"
        "    'nested': {\n"
        "        'a': [1, 2]\n"
        "    }\n"
        "}</pre>"
    )


def test_render_long_list_is_one_item_per_line():
    html = render.render([f"item-{i:02d}-xxxxxxxxxx" for i in range(5)])
    text = html.replace("<br>", "\n")
    assert text.startswith("<pre>[\n    'item-00-xxxxxxxxxx',\n") and text.endswith("    'item-04-xxxxxxxxxx'\n]</pre>")


def test_render_scalars_unchanged():
    assert render.render("0x68 0x69") == "<pre>'0x68 0x69'</pre>"
    assert render.render(42) == "<pre>42</pre>"
