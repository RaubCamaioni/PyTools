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


def literal_to_label(name: str, type: str, default: str):
    default = sanitize_html(default) or ""
    values = parser_literal(type)
    options = [{"value": v, "label": v} for v in values]

    template: Template = TEMPLATES.get_template("components/form_literal.html")
    form = template.render(
        {
            "name": name,
            "options": options,
        },
    )

    return form


def type_to_label(name: str, type: str, default: str):
    default = sanitize_html(default) or ""

    template: Template = TEMPLATES.get_template("components/form_type.html")
    form = template.render(
        {
            "name": name,
            "type": TYPE_MAP.get(type, "text"),
            "default": default,
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


def form_group(name: str, type: str, default: str):
    default = default or ""

    if "Literal" in type:
        return TYPE_TO_LABEL["Literal"](name, type, default)

    if type in TYPE_TO_LABEL:
        return TYPE_TO_LABEL[type](name, type, default)

    return type_to_label(name, "str", "invalid type")


def args_to_form(arguments: dict[str, tuple[str, str]]):
    items = []
    for name, (type, default) in arguments.items():
        items.append(form_group(name, type, default))

    return "\n".join(items)


def list_items(
    base_url: str,
    tools: list[tuple[str, str]],
    end: Optional[int] = None,
    tags: Optional[list[str]] = None,
):
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
                "end": end + 1,
                "tags": " ".join(tags),
            },
        )
        htmlx.append(form)

    return "".join(htmlx)


def list_item_user(root_path: str, tools: list[Tool]):
    template: Template = TEMPLATES.get_template("components/update_tool_item.html")
    htmlx = []

    for tool in tools:
        htmlx.append(
            template.render(
                root_path=root_path,
                id=tool.id,
                name=tool.name,
                public="checked" if tool.public else "",
                anonymous="checked" if tool.annonymous else "",
            )
        )

    return "".join(htmlx)


pretty_printer = MyPrettyPrinter(indent=4, width=50)


def render(results: Any):
    return_string = pretty_printer.pformat(results)

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
