from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends
from typing import Literal, get_origin, Annotated
from starlette.datastructures import UploadFile as StarUploadFile
from app.utility import sandbox, render, serializer, security
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from contextlib import suppress
from pathlib import Path
from app.models import tools as db_tools
import asyncio
import secrets
import logging
import shutil
import string
import time
import stat
import os

logger = logging.getLogger("uvicorn.error")
ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "-_"
APP_DIRECTORY = Path(__file__).parent.parent
TEMPLATES = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    delete_tasks = []
    for task in asyncio.all_tasks():
        if "delete" in task.get_name():
            delete_tasks.append(task)
            task.cancel()
    await asyncio.gather(*delete_tasks)


isolate = sandbox.IsolationWorkers()
router = APIRouter(lifespan=lifespan)


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


Tempdir = Annotated[Path, Depends(get_temp_dir)]


@router.route("/", methods=["GET", "POST"])
async def read_root(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "time": int(time.time()),
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )


@router.get("/tools", response_class=JSONResponse)
async def get_tools(request: Request, session: db_tools.SessionDep):
    tools = db_tools.get_tools(session)
    content = render.list_item(request.scope.get("root_path"), tools)
    return HTMLResponse(content=content)


@router.get("/tool/{id}", response_class=HTMLResponse)
async def entrypoint_page(request: Request, id: int, session: db_tools.SessionDep):
    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    return TEMPLATES.TemplateResponse(
        "tool.html",
        {
            "tool": tool.name,
            "request": request,
            "root_path": request.scope.get("root_path"),
            "endpoint": f"/tool/{tool.id}",
            "code": tool.code,
            "form_groups": tool.arg_form,
            "time": time.time(),
        },
    )


@router.post("/tool/{id}", response_class=HTMLResponse)
async def run_isolated(
    request: Request, temp_dir: Tempdir, session: db_tools.SessionDep
) -> str:
    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    if len(tool.arg_types):
        form_data = await request.form()
    else:
        form_data = {}

    kwargs = {}
    temp_tool = (temp_dir / tool.name).with_suffix(".py")
    with open(temp_tool, "w") as f:
        f.write(tool.code)

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
