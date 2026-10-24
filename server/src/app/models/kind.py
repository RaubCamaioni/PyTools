"""Whether a tool is a model: its entrypoint declares a CadQuery return.

The declaration is read from the code by the sandbox (`Signature.returns`, the annotation as written); the upload
then builds the tool once with its defaults, and only a build that succeeds stores it as a model.
"""

import re
from typing import Optional

# Workplane, Shape, Solid, Compound or Assembly, bare or as cq.X / cadquery.X; nothing wrapped or unioned
CADQUERY_RETURN = re.compile(r"(?:(?:cq|cadquery)\.)?(?:Workplane|Shape|Solid|Compound|Assembly)")


def declares_model(returns: Optional[str]) -> bool:
    return returns is not None and CADQUERY_RETURN.fullmatch(returns.strip()) is not None
