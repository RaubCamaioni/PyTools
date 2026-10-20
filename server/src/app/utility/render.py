import pyparsing as pp
from typing import Any, get_args
from pprint import PrettyPrinter, pformat
from pathlib import Path, PosixPath
from jinja2 import Template
from app import TEMPLATES, logger
from typing import Literal, Optional  # required for form type
from nh3 import clean as sanitize_html
from app.models.tools import Tool


def parser_literal(input: str):
    LITERAL = pp.Suppress(pp.Literal("Literal"))
    OPEN_BRACKET = pp.Suppress(pp.Literal("["))
    CLOSE_BRACKET = pp.Suppress(pp.Literal("]"))
    string_type = pp.Word(pp.alphanums + "_", pp.alphanums + "_.")
    num_type = pp.Combine(
        pp.Optional(".") + pp.Word(pp.nums) + pp.Optional("." + pp.Word(pp.nums))
    )
    empty_quote = string_type | num_type
    single = pp.Suppress("'")
    doube = pp.Suppress('"')
    double_quote = pp.Group(doube + empty_quote + doube).addParseAction(
        lambda t: "".join(t[0])
    )
    single_quote = pp.Group(single + empty_quote + single).addParseAction(
        lambda t: "".join(t[0])
    )
    field = double_quote | single_quote | num_type
    literal_values = pp.ZeroOrMore(field + pp.Suppress(pp.Optional(",")))
    literal_expr = LITERAL + OPEN_BRACKET + literal_values + CLOSE_BRACKET
    return literal_expr.parseString(input)


# TODO: customize web display for more objects
class MyPrettyPrinter(PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, (Path, PosixPath)):
            hyper_link = Path("/download") / object.relative_to(object.anchor)
            download = f'<a href="{hyper_link}" style="white-space: pre;">{object}</a>'

            viewer = ""
            if hyper_link.suffix == ".stl":
                viewer = f'<stl-viewer url="{hyper_link}"></stl-viewer>'

            return (f"{download}{viewer}", True, False)

        return super().format(object, context, maxlevels, level)


def literal_to_label(name: str, type: str, default: str, glyph: str = ""):
    default = sanitize_html(default) or ""
    values = parser_literal(type)
    options = [{"value": v, "label": v} for v in values]

    template: Template = TEMPLATES.get_template("components/form_literal.html")
    form = template.render(
        {
            "name": name,
            "options": options,
            "py_type": "Literal",
            "glyph": glyph,
        },
    )

    return form


def type_to_label(name: str, type: str, default: str, glyph: str = ""):
    default = sanitize_html(default) or ""

    template: Template = TEMPLATES.get_template("components/form_type.html")
    form = template.render(
        {
            "name": name,
            "type": TYPE_MAP.get(type, "text"),
            "default": default,
            "py_type": type,
            "glyph": glyph,
        },
    )

    return form


TYPE_MAP = {
    "str": "text",
    "int": "number",
    "float": "number",
    "Path": "file",
}

TYPE_TO_LABEL = {
    "str": type_to_label,
    "int": type_to_label,
    "float": type_to_label,
    "Path": type_to_label,
    "Literal": literal_to_label,
}


def form_group(name: str, type: str, default: str, glyph: str = ""):
    default = default or ""

    if "Literal" in type:
        return TYPE_TO_LABEL["Literal"](name, type, default, glyph)

    if type in TYPE_TO_LABEL:
        return TYPE_TO_LABEL[type](name, type, default, glyph)

    return type_to_label(name, "str", "invalid type", glyph)


def args_to_form(arguments: dict[str, tuple[str, str]]):
    # rendered as a tree under the function name: tee glyphs, corner on the last argument
    items = []
    last = len(arguments) - 1
    for i, (name, (type, default)) in enumerate(arguments.items()):
        glyph = "└── " if i == last else "├── "
        items.append(form_group(name, type, default, glyph))

    return "\n".join(items)


def list_items(
    base_url: str,
    tools: list[tuple[str, str]],
    end: Optional[int] = None,
    tags: Optional[list[str]] = None,
    page: int = 50,
):
    """Render the ls-style tool list; `end` (if any) is where the next page of `page` tools starts."""
    tags = tags or []

    htmlx = []
    template: Template = TEMPLATES.get_template("components/index_tool_item.html")
    for id, name in tools:
        form = template.render(
            {
                "name": name,
                "id": id,
                "base_url": base_url,
            },
        )
        htmlx.append(form)

    if end is not None:
        template: Template = TEMPLATES.get_template(
            "components/tool_scroll_loader.html"
        )
        form = template.render(
            {
                "start": end,
                "end": end + page,
                "tags": " ".join(tags),
            },
        )
        htmlx.append(form)

    return "".join(htmlx)


# tags carried by only one tool are folded behind [+N more] until a filter is active
COMMON_TAG_MIN_TOOLS = 2


def tag_filters(tag_counts, selected=frozenset(), filtered=False, oob=False) -> str:
    """The `$ head -n1 tools/*.py | grep -i [tag]...` row; `oob` marks it for an htmx out-of-band swap."""
    if filtered:
        common, rare = [t for t, _ in tag_counts], []
    else:
        common = [t for t, n in tag_counts if n >= COMMON_TAG_MIN_TOOLS]
        rare = [t for t, n in tag_counts if n < COMMON_TAG_MIN_TOOLS]
    template: Template = TEMPLATES.get_template("components/tag_filters.html")
    return template.render(common_tags=common, rare_tags=rare, selected=selected, oob=oob)


def format_runs(count: int) -> str:
    """A run count in at most four characters: 9999, 10K, 999K, 1.2M, 12M, 999M, 1.2B."""
    count = max(0, int(count))
    for limit, unit in ((1_000_000_000, "B"), (1_000_000, "M")):
        if count >= 10 * limit:
            return f"{count // limit}{unit}"
        if count >= limit:
            return f"{int(count / limit * 10) / 10:.1f}{unit}"  # floored, so 9 999 999 stays 9.9M
    if count >= 10_000:
        return f"{count // 1_000}K"
    return str(count)


def tool_votes(root_path, tool_id, up, down, my_vote=None, reported=False, login_needed=None) -> str:
    """The [up N] [down N] [report] block of a tool page (components/tool_votes.html)."""
    template: Template = TEMPLATES.get_template("components/tool_votes.html")
    return template.render(
        root_path=root_path or "", tool_id=tool_id, up=up, down=down, my_vote=my_vote, reported=reported, login_needed=login_needed
    )


def list_item_user(root_path: str, tools: list[Tool]):
    template: Template = TEMPLATES.get_template("components/update_tool_item.html")
    # the rows are cells of one grid (`ls -l | column -t`): the header row aligns with them
    htmlx = [
        TEMPLATES.get_template("components/update_tool_header.html").render(),
        TEMPLATES.get_template("components/upload_tool_item.html").render(root_path=root_path),
    ]

    for tool in tools:
        htmlx.append(
            template.render(
                root_path=root_path,
                id=tool.id,
                name=tool.name,
                public="checked" if tool.public else "",
                anonymous="checked" if tool.annonymous else "",
                runs=format_runs(tool.usage),
            )
        )

    return "".join(htmlx)


pretty_printer = MyPrettyPrinter(indent=4, width=50)
INDENT = "    "
INLINE_WIDTH = 50


def pretty(value: Any, depth: int = 0) -> str:
    """Block-style repr: dicts always one entry per line with the closing bracket on its own line,
    lists/tuples/sets the same when they do not fit on one line; scalars via the pretty printer."""
    pad = INDENT * depth
    inner = INDENT * (depth + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        entries = [f"{inner}{pretty_printer.pformat(k)}: {pretty(v, depth + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(entries) + f"\n{pad}}}"
    if isinstance(value, (list, tuple, set, frozenset)):
        flat = pretty_printer.pformat(value)
        if "\n" not in flat and len(flat) <= INLINE_WIDTH:
            return flat
        open_, close = {list: "[]", tuple: "()"}.get(type(value), "{}")
        entries = [f"{inner}{pretty(v, depth + 1)}" for v in value]
        return f"{open_}\n" + ",\n".join(entries) + f"\n{pad}{close}"
    return pretty_printer.pformat(value)


def render(results: Any):
    return_string = pretty(results)

    sanatized = (
        sanitize_html(
            return_string,
            tags={"a", "stl-viewer"},
            attributes={"a": {"href", "style"}, "stl-viewer": {"url"}},
        )
        .replace("\\n", "<br>")
        .replace("\n", "<br>")
    )

    return f"<pre>{sanatized}</pre>"
