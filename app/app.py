from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Any, Dict, Optional
from fastapi.staticfiles import StaticFiles
from dataclasses import dataclass
from pathlib import Path
import subprocess
import ast

import inspect
import time
import os

import logging

logger = logging.getLogger(__name__)


BASE_URL = os.getenv("BASE_URL", "")
logger.info(f"BASE_URL: {BASE_URL}")
router = APIRouter(prefix=BASE_URL)
app = FastAPI()


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: ast.Module):
        self.nodes: List[ast.FunctionDef] = []
        self.visit(module)

    def visit_FunctionDef(self, node):
        self.nodes.append(node)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self.nodes)


class Sandbox:

    def __init__(self, image: str, file: str):
        self.image = image
        self.file = file
        self.command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{file}:/{file}",
            f"{image}",
            "python3",
            f"/{file}",
        ]

    def run(self, args):

        command_with_args = [].extend(self.command)
        command_with_args
        subprocess.call(command_with_args, capture_output=True, text=True)
        print("run_output")


@dataclass
class Tool:
    name: str
    form: str
    source: str


def form_group(name: str, type: str):
    form = "\n".join(
        [
            '<div class="form-group">',
            f'	<label for="{name}">{name}:</label>',
            f'	<input type="{type}" id="{name}" name="{name}" step=".01" required>',
            "</div>",
        ]
    )
    return form


def load_tools(converters_folder: Path) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}

    for converter_file in converters_folder.glob("*.py"):
        tool_name = converter_file.stem

        with open(converter_file, "r") as f:
            source = "".join(f.readlines()).strip()

        tree = ast.parse(source)
        entry_node = None
        for node in FunctionVisitor(tree):
            comment = source.splitlines()[max(node.lineno - 2, 0)]
            if "#entrypoint" in comment.replace(" ", ""):
                entry_node = node
                break

        if entry_node is None:
            logger.warning(f"no entrypoint foudn in: {tool_name}")
            continue

        arg_form = []
        arg_types = {}
        for arg in entry_node.args.args:

            if not arg.annotation:
                logger.warning(
                    f"all arguments in entrypoint ({tool_name}) must be annotated"
                )

            arg_name, arg_type = arg.arg, ast.unparse(arg.annotation)

            arg_types[arg_name] = arg_type

            form_type = {
                "str": "text",
                "int": "number",
                "float": "number",
            }

            arg_form.append(form_group(arg.arg, form_type.get(arg_type, "text")))

        converter_module = Tool(
            name=tool_name,
            source=source,
            form="\n".join(arg_form),
        )

        logger.info(f"loaded converter: {tool_name}")
        tools[tool_name] = converter_module

    return tools


TOOLS = load_tools(Path(__file__).parent / "converters")
TEMPLATES = Jinja2Templates(directory="templates")
app.mount(f"{BASE_URL}/static", StaticFiles(directory="static"), name="static")
app.mount(f"{BASE_URL}/scripts", StaticFiles(directory="scripts"), name="scripts")


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "base_url": BASE_URL,
        },
    )


@router.get("/tools", response_class=JSONResponse)
async def get_tools():
    tools = [e.name for e in TOOLS.values()]
    return {"tools": tools}


@router.get("/tool/{tool_name}", response_class=HTMLResponse)
async def entrypoint_page(request: Request, tool_name: str):

    if not (tool := TOOLS.get(tool_name, None)):
        raise HTTPException(status_code=404, detail="Entrypoint not found")

    return TEMPLATES.TemplateResponse(
        "converter.html",
        {
            "request": request,
            "endpoint": f"/tool/{tool.name}",
            "converter_name": tool.name,
            "code": tool.source,
            "form_groups": tool.form,
            "time": time.time(),
            "base_url": BASE_URL,
        },
    )


@router.post("/tool/{tool_name}", response_class=HTMLResponse)
async def run_entrypoint_in_sandbox(request: Request, tool_name: str) -> str:

    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="Converter module not found")
    module = TOOLS[tool_name]
    form_data = await request.form()

    # parse the form data and run code in isolated docker container...

    kwargs = {}
    for key, value in form_data.items():
        kwargs[key] = module.types[key](value)

    result = None
    return_string = f"{type(result).__name__}: {result}"

    structure = f'<div id="result" class="result-container"><div class="return">{return_string}</div></div>'

    return HTMLResponse(structure)


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
