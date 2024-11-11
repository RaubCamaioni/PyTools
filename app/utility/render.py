from typing import Any
from pprint import PrettyPrinter
from pathlib import Path, PosixPath


class MyPrettyPrinter(PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, (Path, PosixPath)):
            hyper_link = Path("/download") / object.relative_to(object.anchor)
            return (
                f'<a href="{hyper_link}" style="white-space: pre;">{object}</a>',
                True,
                False,
            )
        return super().format(object, context, maxlevels, level)


pp = MyPrettyPrinter(indent=4, width=1)


def render(results: Any):
    return_string = pp.pformat(results)
    structure = f'<div class="container" id="result" ><div class="return"><pre>{return_string}</pre></div></div>'
    return structure
