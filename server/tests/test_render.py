from pathlib import Path
import pytest
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


def test_number_arguments_are_typed_not_spun():
    html = render.args_to_form({"ratio": ("float", "0.3"), "count": ("int", "2")})
    assert 'type="number"' not in html and html.count('inputmode="decimal"') == 2


def test_argument_inputs_are_console_fields():
    html = render.args_to_form({"count": ("int", "1"), "mode": ("Literal['a', 'b']", "a")})
    assert html.count('<span class="field') == 1 and html.count('<span class="pick') == 1  # text: underscore caret; list: arrow


def test_user_tool_table_starts_with_a_header_row():
    from app.models.tools import Tool

    html = render.list_item_user("", [Tool(id=1, name="a", code="", public=True, annonymous=True, usage=3, tags=[])])
    assert html.index("NAME") < html.index("MODE") < html.index("RUNS") < html.index("ACTIONS") < html.index("a.py")
    assert html.index("a.py") < html.index("[public]")  # the name, the row's identifier, comes first
    assert html.index("ACTIONS") < html.index("[upload]") < html.index("a.py")  # the upload row leads the table
    assert html.count('<li class="contents') == 3  # header + upload row + one tool row, all grid rows
    assert html.count(">---<") == 3  # name, mode and runs do not apply to the upload row; [upload] is its action


@pytest.mark.parametrize(
    "count, text",
    [(0, "0"), (9999, "9999"), (10000, "10K"), (12345, "12K"), (999999, "999K"), (1000000, "1.0M"),
     (1234567, "1.2M"), (9999999, "9.9M"), (10000000, "10M"), (999999999, "999M"), (1000000000, "1.0B")],
)
def test_format_runs_fits_four_characters(count, text):
    assert render.format_runs(count) == text and len(text) <= 4


def test_result_paths_render_as_download_links():
    html = render.render(Path("/tmp/pywebtools-runs/abc/qr_code.png"))
    assert 'href="/download/tmp/pywebtools-runs/abc/qr_code.png"' in html.replace("\\", "/")
    assert 'download="qr_code.png"' in html
