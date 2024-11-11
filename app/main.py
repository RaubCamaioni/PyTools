from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile as StarUploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager, suppress
from .utility import serializer, render
from typing import List, Dict, Type
from dataclasses import dataclass
from pathlib import Path
import subprocess
import logging
import asyncio
import secrets
import shutil
import string
import time
import ast
import os


logger = logging.getLogger("uvicorn.error")


router = APIRouter()


ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "-_"


def secret_dir_name(length=32):
    return "".join(secrets.choice(ALLOWED_CHARACTERS) for _ in range(length))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    shutdown_event.set()

    delete_tasks = []
    for task in asyncio.all_tasks():
        if "delete" in task.get_name():
            delete_tasks.append(task)
    await asyncio.gather(*delete_tasks)


shutdown_event = asyncio.Event()
app = FastAPI(lifespan=lifespan)


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: ast.Module):
        self.nodes: List[ast.FunctionDef] = []
        self.visit(module)

    def visit_FunctionDef(self, node):
        self.nodes.append(node)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self.nodes)


def docker_run(image: str, tool: Path, workdir: Path):
    command = [
        "docker",
        "run",
        "--network=none",
        "-m=512m",
        "--cpus=1.5",
        "--rm",
        "-v",
        f"{tool}:/sandbox/{tool.name}:ro",
        "-v",
        f"{workdir}:{'/sandbox' / workdir}",
        f"{image}",
        "python3",
        "runner.py",
        "--file",
        f"/sandbox/{tool.name}",
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


def form_group(name: str, type: str, default: str):
    default = default or ""

    form = "\n".join(
        [
            '<div class="form-group">',
            f'	<label for="{name}">{name}:</label>',
            f'	<input type="{type}" id="{name}" name="{name}" step=".01" required value="{default}">',
            "</div>",
        ]
    )
    return form


def load_tools(tools_directory: Path) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}

    for tool_file in tools_directory.glob("*.py"):
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

        default_args = [None] * len(entry_node.args.args)
        for i, default in enumerate(entry_node.args.defaults):
            default_args[-i] = ast.unparse(default)

        for arg, default in zip(entry_node.args.args, default_args):
            if not arg.annotation:
                logger.warning(
                    f"all arguments in entrypoint ({tool_name}) must be annotated"
                )

            arg_name, arg_type = arg.arg, ast.unparse(arg.annotation)

            if arg_type not in ["int", "float", "str", "Path"]:
                logger.warning(f"invalid arg_type {arg_type} in {tool_name}")
                continue

            arg_types[arg_name] = eval(arg_type)

            form_type = {
                "str": "text",
                "int": "number",
                "float": "number",
                "Path": "file",
            }

            arg_form.append(
                form_group(arg.arg, form_type.get(arg_type, "text"), default)
            )

        tool_arg_string = []
        for k, v in arg_types.items():
            tool_arg_string.append(f"  {k}: {v}")
        tool_arg_string = "\n".join(tool_arg_string)
        logger.info(f"Loading Tool: {tool_name}\n{tool_arg_string}")

        tool = Tool(
            file=tool_file,
            name=tool_name,
            source=source,
            arg_types=arg_types,
            form="\n".join(arg_form),
        )

        tools[tool_name] = tool

    return tools


APP_DIRECTORY = Path(__file__).parent
TOOLS = load_tools(APP_DIRECTORY / "tools")
TEMPLATES = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
app.mount("/scripts", StaticFiles(directory=APP_DIRECTORY / "scripts"), name="scripts")


async def delete_temp_dir(temp_dir: Path):
    with suppress(asyncio.TimeoutError):
        await asyncio.wait_for(shutdown_event.wait(), timeout=60 * 5)

    if temp_dir.exists() and temp_dir.is_dir():
        shutil.rmtree(temp_dir)


async def get_temp_dir():
    temp_dir = Path("/tmp") / secret_dir_name(32)
    os.mkdir(temp_dir)
    yield temp_dir
    asyncio.create_task(delete_temp_dir(temp_dir), name=f"delete-{temp_dir}")


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "root_path": request.scope.get("root_path"),
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
        "tool.html",
        {
            "request": request,
            "root_path": request.scope.get("root_path"),
            "endpoint": f"/tool/{tool.name}",
            "code": tool.source,
            "form_groups": tool.form,
            "time": time.time(),
        },
    )


@router.post("/tool/{tool_name}", response_class=HTMLResponse)
async def run_entrypoint_in_sandbox(
    request: Request,
    tool_name: str,
    temp_dir: Path = Depends(get_temp_dir),
) -> str:
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="tool module not found")

    tool = TOOLS[tool_name]
    form_data = await request.form()

    kwargs = {}
    for key, value in form_data.items():
        if key == "__blank__":  # fixes empty submit error
            continue

        python_type = tool.arg_types[key]

        if isinstance(value, StarUploadFile):
            with open(temp_dir / value.filename, "wb+") as f:
                f.write(value.file.read())
            kwargs[key] = temp_dir / value.filename
        else:
            kwargs[key] = python_type(value)

    with open(temp_dir / "args.json", "w") as f:
        serializer.dump(kwargs, f)

    docker_run("sandbox:latest", Path(tool.file), Path(temp_dir))

    results_file = temp_dir / "result.json"
    if not results_file.exists():
        results = Exception("Falure to produce results!")
    else:
        with open(temp_dir / "result.json", "r") as f:
            results = serializer.load(f)

    structure = render.render(results)

    return HTMLResponse(structure)


app.include_router(router)


@app.get("/download/{file_str:path}")
async def download_file(file_str: str):
    file_path = Path("/") / Path(file_str)
    logger.info(f"File Path: {file_path}")

    if not file_path.is_absolute():
        raise HTTPException(
            status_code=400, detail="Invalid path: Only absolute paths are allowed."
        )

    if not file_path.parts[1] == "tmp":
        raise HTTPException(
            status_code=403, detail=f"Forbidden File Access: {file_path.parts[0]}"
        )

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=file_path.name,
    )


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
