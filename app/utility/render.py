from typing import Any
from pprint import PrettyPrinter, pformat
from pathlib import Path, PosixPath

# TODO: added multi choice literal to form

TYPE_MAP = {
    "str": "text",
    "int": "number",
    "float": "number",
    "Path": "file",
}


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


def form_group(name: str, type: str, default: str):
    default = default or ""
    form_type = TYPE_MAP.get(type, "text")

    form = "\n".join(
        [
            '<div class="form-group">',
            f'	<label for="{name}">{name}:</label>',
            f'	<input type="{form_type}" id="{name}" name="{name}" step=".01" required value="{default}">',
            "</div>",
        ]
    )
    return form


pp = MyPrettyPrinter(indent=4, width=10**5)


def render(results: Any):
    return_string = pp.pformat(results)
    print(return_string)
    structure = f'<div class="container" id="result" ><div class="return"><pre>{return_string}</pre></div></div>'
    return structure
