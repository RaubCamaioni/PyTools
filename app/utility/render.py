import pyparsing as pp
from typing import Any, get_args, Literal
from pprint import PrettyPrinter, pformat
from pathlib import Path, PosixPath
import ast


def parser_literal(input: str):
    LITERAL = pp.Literal("Literal")
    OPEN_BRACKET = pp.Literal("[")
    CLOSE_BRACKET = pp.Literal("]")
    literal_type = pp.Word(pp.alphas + "_.", pp.alphanums + "_.")
    double_quote = '"' + literal_type + '"'
    single_quote = "'" + literal_type + "'"
    field = double_quote ^ single_quote
    literal_values = pp.ZeroOrMore(field + pp.Optional(","))
    literal_expr = LITERAL + OPEN_BRACKET + literal_values + CLOSE_BRACKET
    return "".join(literal_expr.parseString(input))


# TODO: improve string representation of objects
class MyPrettyPrinter(PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, (Path, PosixPath)):
            hyper_link = Path("/download") / object.relative_to(object.anchor)
            return (
                f'<a href="{hyper_link}" style="white-space: pre;">{object}</a>',
                True,
                False,
            )
        if isinstance(object, list) and level == 0:  # Split lists only at the top level
            return (
                "[" + ",\n".join(pformat(item, width=10000) for item in object) + "]",
                True,
                False,
            )

        return super().format(object, context, maxlevels, level)


def literal_to_label(name: str, type: str, default: str):
    default = default or ""

    option = """<option value="{option}">{option}</option>"""

    values = get_args(eval(parser_literal(type)))

    form = f"""
    <label for="{name}">{name}:</label>
    <select id="{name}" name="{name}">
    {"\n".join([option.format(option=o) for o in values])}
    </select>
    """

    return form


def type_to_label(name: str, type: str, default: str):
    default = default or ""

    form = f"""
    <div class="form-group">
    <label for="{name}">{name}:</label>
    <input type="{TYPE_MAP.get(type, "text")}" id="{name}" name="{name}" step=".01" required value="{default}">
    </div>
    """

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
    else:
        return TYPE_TO_LABEL[type](name, type, default)


def list_item(base_url: str, tools: list):
    htmlx = []
    for e in tools.values():
        htmlx.append(f'<li><a href="{base_url}/tool/{e.name}">{e.name}</a></li>')
    return "".join(htmlx)


pretty_printer = MyPrettyPrinter(indent=4, width=10**5)


def render(results: Any):
    return_string = pretty_printer.pformat(results)
    structure = f'<div class="container" id="result" ><div class="return"><pre>{return_string}</pre></div></div>'
    return structure
