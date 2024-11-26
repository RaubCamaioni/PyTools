from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends
from typing import List, Dict, Type, Literal, get_origin, Annotated
from starlette.datastructures import UploadFile as StarUploadFile
from app.utility import sandbox, render, serializer, security
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from app.models.tools import SessionDep, User
from dataclasses import dataclass
from contextlib import suppress
from pathlib import Path
import asyncio
import secrets
import logging
import shutil
import string
import time
import stat
import ast
import os

logger = logging.getLogger("uvicorn.error")
ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "-_"
APP_DIRECTORY = Path(__file__).parent.parent
TEMPLATES = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tools = load_tools(APP_DIRECTORY / "tools")
    yield
    delete_tasks = []
    for task in asyncio.all_tasks():
        if "delete" in task.get_name():
            delete_tasks.append(task)
            task.cancel()
    await asyncio.gather(*delete_tasks)


isolate = sandbox.IsolationWorkers()
router = APIRouter(lifespan=lifespan)


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: ast.Module):
        self.nodes: List[ast.FunctionDef] = []
        self.visit(module)

    def visit_FunctionDef(self, node):
        self.nodes.append(node)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self.nodes)


@dataclass
class Tool:
    name: str
    form: str
    source: str
    arg_types: Dict[str, Type]


def load_tool(tool_name: str, tool_source: str):
    tree = ast.parse(tool_source)

    entry_node = None
    for node in FunctionVisitor(tree):
        if tool_name == node.name:
            entry_node = node

    if entry_node is None:
        logger.warning(f"no entrypoint found in: {tool_name}")
        return None

    arg_form = []
    arg_types = {}

    default_args = [None] * len(entry_node.args.args)
    for i, default in enumerate(entry_node.args.defaults[::-1]):
        default_args[-i - 1] = ast.unparse(default)

    skip_tool = False
    for arg, default in zip(entry_node.args.args, default_args):
        if not arg.annotation:
            logger.warning(f"{tool_name} arguments must be annotated")
            skip_tool = True
            break

        arg_name, arg_type = arg.arg, ast.unparse(arg.annotation)

        base_type = arg_type not in ["int", "float", "str", "Path"]
        literal_type = "Literal" not in arg_type
        if base_type and literal_type:
            logger.warning(f"invalid arg_type {arg_type} in {tool_name}")
            skip_tool = True
            break

        if not base_type:
            arg_types[arg_name] = eval(arg_type)
        elif not literal_type:
            arg_types[arg_name] = eval(render.parser_literal(arg_type))

        arg_form.append(render.form_group(arg.arg, arg_type, default))

    if skip_tool:
        return None

    tool_arg_string = []
    for k, v in arg_types.items():
        tool_arg_string.append(f"  {k}: {v}")
    tool_arg_string = "\n".join(tool_arg_string)
    logger.info(f"Loading Tool: {tool_name}\n{tool_arg_string}")

    return Tool(
        name=tool_name,
        source=tool_source,
        arg_types=arg_types,
        form="\n".join(arg_form),
    )


def load_tools(tools_directory: Path) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}

    for tool_file in tools_directory.glob("*.py"):
        tool_name = tool_file.stem

        with open(tool_file, "r") as f:
            tool_source = "".join(f.readlines()).strip()

        tool = load_tool(tool_name, tool_source)

        if tool is None:
            continue

        tools[tool_name] = tool

    return tools


def secret_dir_name(length=32):
    return "".join(secrets.choice(ALLOWED_CHARACTERS) for _ in range(length))


async def delete_temp_dir(temp_dir: Path):
    try:
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(60 * 10)
    finally:
        if temp_dir.exists() and temp_dir.is_dir():
            shutil.rmtree(temp_dir)


async def get_temp_dir():
    try:
        temp_dir = Path("/tmp") / secret_dir_name(32)
        os.mkdir(temp_dir)
        os.chmod(temp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        yield temp_dir
    finally:
        task = delete_temp_dir(temp_dir)
        asyncio.create_task(task, name=f"delete-{temp_dir}")


@router.route("/", methods=["GET", "POST"])
async def read_root(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "time": time.time(),
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )


@router.get("/tools", response_class=JSONResponse)
async def get_tools(request: Request):
    tools: dict[str, Tool] = request.app.state.tools
    content = render.list_item(request.scope.get("root_path"), tools)
    return HTMLResponse(content=content)


@router.get("/tool/{tool_name}", response_class=HTMLResponse)
async def entrypoint_page(request: Request, tool_name: str):
    tools: dict[str, Tool] = request.app.state.tools
    if not (tool := tools.get(tool_name, None)):
        raise HTTPException(status_code=404, detail="Tool Not Found")

    return TEMPLATES.TemplateResponse(
        "tool.html",
        {
            "tool": tool.name,
            "request": request,
            "root_path": request.scope.get("root_path"),
            "endpoint": f"/tool/{tool.name}",
            "code": tool.source,
            "form_groups": tool.form,
            "time": time.time(),
        },
    )


@router.post("/tool/{tool_name}", response_class=HTMLResponse)
async def run_isolated(
    request: Request,
    tool_name: str,
    temp_dir: Annotated[Path, Depends(get_temp_dir)],
) -> str:
    tools: dict[str, Tool] = request.app.state.tools
    if tool_name not in tools:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    tool = tools[tool_name]

    if len(tool.arg_types):
        form_data = await request.form()
    else:
        form_data = {}

    kwargs = {}
    temp_tool = (temp_dir / tool.name).with_suffix(".py")
    with open(temp_tool, "w") as f:
        f.write(tool.source)

    for key, value in form_data.items():
        python_type = tool.arg_types[key]

        if isinstance(value, StarUploadFile):
            upload_path = temp_dir / value.filename
            with open(upload_path, "wb+") as f:
                f.write(value.file.read())
            kwargs[key] = upload_path
        elif get_origin(python_type) is Literal:
            kwargs[key] = str(value)
        else:
            kwargs[key] = python_type(value)

    with open(temp_dir / "args.json", "w") as f:
        serializer.dump(kwargs, f)

    # !DANGER! user submitted code
    isolate.run(temp_tool, temp_dir)

    results_file = temp_dir / "result.json"
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="Runner Failed")

    with open(results_file, "r") as f:
        results = serializer.load(f)

    return HTMLResponse(content=render.render(results))


@security.constant_time_with_random_delay(0.2, 1)
@router.get("/download/{file_str:path}", response_class=FileResponse)
async def download_file(file_str: str):
    file_path = Path("/") / Path(file_str)
    file_path = file_path.resolve()

    forbidden = HTTPException(status_code=403, detail="Forbidden File Access")

    if not str(file_path).startswith("/tmp/"):
        raise forbidden

    if not file_path.exists():
        raise forbidden

    if not file_path.is_file():
        raise forbidden

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@router.get("/terms-of-service", response_class=FileResponse)
async def terms_of_service(request: Request):
    kwargs = {"request": request}
    return TEMPLATES.TemplateResponse("terms_of_service.html", kwargs)


@router.get("/privacy-policy", response_class=FileResponse)
async def privacy_policy(request: Request):
    kwargs = {"request": request}
    return TEMPLATES.TemplateResponse("privacy_policy.html", kwargs)
