from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends
from starlette.datastructures import UploadFile as StarUploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Type
import subprocess
import tempfile
import utility
import json
import ast

import time
import os

import logging

import utility.serializer

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


def docker_run(image: str, file: Path, workdir: Path):
    command = [
        "docker",
        "run",
        "-m=512m",
        "--cpus=1.5",
        "--rm",
        "-v",
        f"{file}:/sandbox/{file.name}",
        "-v",
        f"{workdir}:{'/sandbox' / workdir}",
        f"{image}",
        "python3",
        "runner.py",
        "--file",
        f"/sandbox/{file.name}",
        "--workdir",
        f"{'sandbox' / workdir}",
    ]
    subprocess.call(command)


@dataclass
class Tool:
    file: str
    name: str
    form: str
    source: str
    arg_types: Dict[str, Type]


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

    for tool_file in converters_folder.glob("*.py"):
        tool_name = tool_file.stem

        with open(tool_file, "r") as f:
            source = "".join(f.readlines()).strip()

        tree = ast.parse(source)
        entry_node = None
        for node in FunctionVisitor(tree):
            if tool_name == node.name:
                entry_node = node

        if entry_node is None:
            logger.warning(f"no entrypoint found in: {tool_name}")
            continue

        arg_form = []
        arg_types = {}
        for arg in entry_node.args.args:
            if not arg.annotation:
                logger.warning(
                    f"all arguments in entrypoint ({tool_name}) must be annotated"
                )

            arg_name, arg_type = arg.arg, ast.unparse(arg.annotation)

            if arg_type not in ["int", "float", "Path", "str"]:
                logger.warning(f"invalid arg_type {arg_type} in {tool_name}")
                continue

            arg_types[arg_name] = eval(arg_type)

            form_type = {
                "str": "text",
                "int": "number",
                "float": "number",
                "Path": "file",
            }

            arg_form.append(form_group(arg.arg, form_type.get(arg_type, "text")))

        converter_module = Tool(
            file=tool_file,
            name=tool_name,
            source=source,
            arg_types=arg_types,
            form="\n".join(arg_form),
        )

        logger.info(f"loaded converter: {tool_name}")
        tools[tool_name] = converter_module

    return tools


TOOLS = load_tools(Path(__file__).parent / "converters")
TEMPLATES = Jinja2Templates(directory="templates")
app.mount(f"{BASE_URL}/static", StaticFiles(directory="static"), name="static")
app.mount(f"{BASE_URL}/scripts", StaticFiles(directory="scripts"), name="scripts")


async def get_temp_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


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
async def run_entrypoint_in_sandbox(
    request: Request,
    tool_name: str,
    temp_dir: str = Depends(get_temp_dir),
) -> str:
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="Converter module not found")
    tool = TOOLS[tool_name]
    form_data = await request.form()

    temp_path = Path(temp_dir)

    kwargs = {}
    for key, value in form_data.items():
        python_type = tool.arg_types[key]

        if isinstance(value, StarUploadFile):
            with open(temp_path / value.filename, "wb+") as f:
                f.write(value.file.read())
            kwargs[key] = temp_path / value.filename
        else:
            kwargs[key] = python_type(value)

    with open(temp_path / "args.json", "w") as f:
        utility.serializer.dump(kwargs, f)

    docker_run("sandbox:latest", Path(tool.file), Path(temp_dir))

    results_file = temp_path / "result.json"
    if not results_file.exists():
        results = Exception("Falure to produce results!")
    else:
        with open(temp_path / "result.json", "r") as f:
            results = json.load(f)

    return_string = f"{type(results).__name__}: {results}"
    structure = f'<div class="container" id="result" ><div class="return">{return_string}</div></div>'

    return HTMLResponse(structure)


app.include_router(router)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
