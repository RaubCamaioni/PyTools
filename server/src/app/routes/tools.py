from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
    FileResponse,
)
from urllib.parse import (
    unquote,
    parse_qs,
    quote_plus,
    urlparse,
    ParseResultBytes,
    urljoin,
    urlencode,
)
from fastapi import FastAPI, HTTPException, Request, APIRouter, Depends, Query
from starlette.datastructures import UploadFile as StarUploadFile
from typing import Literal, get_origin, Annotated, Optional
from contextlib import asynccontextmanager, suppress
from zipfile import ZipFile
from pathlib import Path
from io import BytesIO
import asyncio
import secrets
import shutil
import time
import stat
import os

from app.utility import render, serializer, security
from app.utility.podman_runner import PodmanRunner, Outcome, SandboxBusy, SandboxUnavailable
from app.utility.trace import TraceRegistry
from app import TEMPLATES, ALLOWED_CHARACTERS, logger, ENVIRONMENT
from app.models import tools as db_tools
from app.routes.auth import User
import json
import re
from pathlib import PosixPath


class PathEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PosixPath):
            return str(obj)
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # pages are served immediately; tool runs return 503 until the sandbox self-test passes
    runner.start_in_background()
    yield
    delete_tasks = []
    for task in asyncio.all_tasks():
        if "delete" in task.get_name():
            delete_tasks.append(task)
            task.cancel()
    await asyncio.gather(*delete_tasks)
    await runner.stop()


runner = PodmanRunner(ENVIRONMENT.sandbox)
router = APIRouter(lifespan=lifespan)

# execution trace: the tool page registers a random token with its run and streams the run's
# line numbers from /trace/{token} (docs/superpowers/specs/2026-10-19-execution-trace-design.md)
TRACES = TraceRegistry()
TRACE_TOKEN = re.compile(r"[A-Za-z0-9_-]{32}")
TRACE_HEADER = "X-Trace-Token"
TRACE_WAIT_SECONDS = 10.0  # how long a stream waits for its run to be registered
TRACE_POLL_SECONDS = 0.05
TRACE_IDLE_SECONDS = 1.0  # between checks that the stream was not superseded


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
        run_root = ENVIRONMENT.sandbox.run_dir
        run_root.mkdir(parents=True, exist_ok=True)
        temp_dir = run_root / secret_dir_name(32)
        os.mkdir(temp_dir)
        os.chmod(temp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        yield temp_dir
    finally:
        task = delete_temp_dir(temp_dir)
        asyncio.create_task(task, name=f"delete-{temp_dir}")


Tempdir = Annotated[Path, Depends(get_temp_dir)]


@router.get("/healthz")
async def healthz():
    if runner.available:
        return JSONResponse({"sandbox": "ready"})
    return JSONResponse({"sandbox": "unavailable", "reason": runner.unavailable_reason}, status_code=503)


@router.get("/trace/{token}")
async def trace_stream(token: str):
    if not TRACE_TOKEN.fullmatch(token):
        raise HTTPException(status_code=404, detail="Not Found")

    async def wait_for_channel():
        deadline = time.monotonic() + TRACE_WAIT_SECONDS
        while (channel := TRACES.get(token)) is None and time.monotonic() < deadline:
            await asyncio.sleep(TRACE_POLL_SECONDS)
        return channel

    async def stream():
        channel = await wait_for_channel()
        if channel is not None:
            ticket = channel.attach()
            while True:
                try:
                    line = await asyncio.wait_for(channel.queue.get(), TRACE_IDLE_SECONDS)
                except asyncio.TimeoutError:
                    superseded = channel.ticket != ticket or TRACES.get(token) not in (channel, None)
                    if superseded or channel.closed:  # closed: a later stream found the end marker already taken
                        break
                    continue
                if line is None:
                    break
                yield f"event: line\ndata: {line}\n\n"
        yield "event: end\ndata:\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.api_route("/", methods=["GET", "POST"])
async def read_root(request: Request, session: db_tools.SessionDep):
    return TEMPLATES.TemplateResponse(
        request,
        "pages/index.html",
        {
            "header_title": "PyTools",
            "request": request,
            "root_path": request.scope.get("root_path"),
            "tag_filters": render.tag_filters(db_tools.get_tag_counts(session)),
        },
    )


@router.post("/tools", response_class=JSONResponse)
async def get_tools(
    request: Request,
    session: db_tools.SessionDep,
    start: int = Query(0, ge=0),
    end: int = Query(100, ge=0),
):
    if start > end:
        raise HTTPException(status_code=400, detail="Invalid index range")

    body = await request.body()
    search_string = unquote(body.decode())
    query_params = parse_qs(search_string)
    # typed grep pattern plus the selected first-line hashtags, all ANDed by the query
    tags = query_params.get("search", [""])[0].split() + [t for t in query_params.get("tag", []) if t.strip()]

    if tags:
        tools = db_tools.get_tools_by_tags(session, tags, start, end)
    else:
        tools = db_tools.get_tools_by_index(session, start, end)

    if len(tools) < (end - start):
        end = None

    content = render.list_items(request.scope.get("root_path"), tools, end, tags, page=end - start if end else 50)

    if start == 0:
        # a new filter (not a scrolled page): swap in the tags that overlap the matching tools
        content += render.tag_filters(
            db_tools.get_tag_counts(session, tags),
            selected={t for t in query_params.get("tag", []) if t.strip()},
            filtered=bool(tags),
            oob=True,
        )

    return HTMLResponse(content=content)


@router.post("/user/tools", response_class=JSONResponse)
async def get_user_tools(request: Request, session: db_tools.SessionDep):
    if "user" not in request.session:
        return HTMLResponse(content="")
    user: User = User.model_validate_json(request.session["user"])
    tools = db_tools.get_user_tools(session, user)
    content = render.list_item_user(request.scope.get("root_path"), tools)
    return HTMLResponse(content=content)


# currently unused
@router.get("/tool/{id}/link", response_class=HTMLResponse)
async def tool_link(request: Request, id: int, session: db_tools.SessionDep):
    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    if not tool.public:
        if "user" not in request.session:
            raise HTTPException(status_code=404, detail="Tool Not Found")
        user: User = User.model_validate_json(request.session["user"])

        if tool.user_id != user.id:
            raise HTTPException(status_code=404, detail="Tool Not Found")

    form_data = {}
    if len(tool.arguments):
        form_data = await request.form()

    parsed_url: ParseResultBytes = urlparse(str(request.url))
    root_path = request.scope.get("root_path")

    url = urljoin(
        f"{parsed_url.scheme}://{parsed_url.netloc}",
        f"{root_path}/tool/{id}",
    )

    query_string = urlencode(form_data)
    content = f"{url}?{query_string}"

    return HTMLResponse(content=content)


@router.get("/tool/{id}", response_class=HTMLResponse)
async def entrypoint_page(request: Request, id: int, session: db_tools.SessionDep):
    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    if not tool.public:
        if "user" not in request.session:
            raise HTTPException(status_code=404, detail="Tool Not Found")
        user: User = User.model_validate_json(request.session["user"])
        if tool.user_id != user.id:
            raise HTTPException(status_code=404, detail="Tool Not Found")

    query = dict(request.query_params)
    arguments = tool.arguments

    for name, default in query.items():
        if name not in arguments:
            continue
        t, d = arguments[name]
        arguments[name] = (t, default)

    return TEMPLATES.TemplateResponse(
        request,
        "pages/tool.html",
        {
            "header_title": "PyTools",
            "tool": tool.name,
            "tool_id": tool.id,
            "runs": tool.usage,
            "request": request,
            "root_path": request.scope.get("root_path"),
            "endpoint": f"/tool/{tool.id}",
            "code": tool.code,
            "lines": tool.code.count("\n") + 1,
            "form_groups": render.args_to_form(tool.arguments),
            "time": time.time(),
        },
    )


@router.get("/download/tool/{id}", response_class=HTMLResponse)
async def download_tool(request: Request, id: int, session: db_tools.SessionDep):
    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    if not tool.public:
        if "user" not in request.session:
            raise HTTPException(status_code=404, detail="Tool Not Found")
        user: User = User.model_validate_json(request.session["user"])
        if tool.user_id != user.id:
            raise HTTPException(status_code=404, detail="Tool Not Found")

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr(f"{tool.name}.py", tool.code)
        zip_file.write("/files/runner.py", "runner.py")
        zip_file.write("/files/requirements.txt", "requirements.txt")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={tool.name}.zip"},
    )


@router.get("/public/tool/{id}", response_class=HTMLResponse)
async def public_tool(
    request: Request,
    id: int,
    session: db_tools.SessionDep,
    public: bool = False,
):
    if "user" not in request.session:
        raise HTTPException(status_code=403, detail="Forbidden")

    user: User = User.model_validate_json(request.session.get("user"))
    tool = db_tools.get_tool_by_id(session, id)

    if user.id != tool.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    tool.public = public
    session.commit()

    return HTMLResponse(status_code=200)


async def _run_tool(request: Request, id: int, temp_dir: Path, session, channel):
    if not runner.available:
        raise HTTPException(status_code=503, detail="Sandbox unavailable")

    tool = db_tools.get_tool_by_id(session, id)

    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")

    if not tool.public:
        if "user" not in request.session:
            raise HTTPException(status_code=404, detail="Tool Not Found")
        user: User = User.model_validate_json(request.session["user"])
        if tool.user_id != user.id:
            raise HTTPException(status_code=404, detail="Tool Not Found")

    form_data = {}
    if len(tool.arguments):
        form = await request.form()
        form_data = {k: v for k, v in form.items() if k in tool.arguments}  # stray fields are ignored

    kwargs = {}
    temp_tool = (temp_dir / tool.name).with_suffix(".py")
    with open(temp_tool, "w") as f:
        f.write(tool.code)

    for key, value in form_data.items():
        # TODO: saftey check: tool arguments have been parsed at this point (maybe pre cast them?)
        python_type = eval(tool.arguments[key][0])

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

    tool.usage = tool.usage + 1
    session.commit()

    # !DANGER! user submitted code
    try:
        return await runner.run(temp_tool, temp_dir, on_line=channel.put if channel is not None else None)
    except SandboxBusy:
        raise HTTPException(status_code=503, detail="Server busy, try again")
    except SandboxUnavailable:
        raise HTTPException(status_code=503, detail="Sandbox unavailable")


@router.post("/tool/{id}", response_class=HTMLResponse)
async def run_isolated(
    request: Request,
    id: int,
    temp_dir: Tempdir,
    session: db_tools.SessionDep,
) -> str:
    # the page sends its trace token as a header so it can never collide with a tool argument
    token = request.headers.get(TRACE_HEADER, "")
    channel = None
    if TRACE_TOKEN.fullmatch(token):
        TRACES.expire()
        channel = TRACES.register(token)
    try:
        result = await _run_tool(request, id, temp_dir, session, channel)
    finally:
        if channel is not None:
            channel.close()  # every exit, including 404/503, ends the page's trace stream

    htmx = request.headers.get("HX-Request") == "true"

    if result.outcome is not Outcome.OK:
        logger.warning(f"tool {id} {result.outcome.name}: {result.stderr_tail}")
        if htmx:
            text = result.message + (f"\n{result.stderr_tail}" if result.stderr_tail else "")
            return HTMLResponse(content=render.render(text))
        return JSONResponse({"detail": result.message})

    if htmx:
        return HTMLResponse(content=render.render(result.results))
    else:
        return json.dumps(result.results, cls=PathEncoder)


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
    kwargs = {"request": request, "header_title": "PyTools"}
    return TEMPLATES.TemplateResponse(request, "pages/terms_of_service.html", kwargs)


@router.get("/privacy-policy", response_class=FileResponse)
async def privacy_policy(request: Request):
    kwargs = {"request": request, "header_title": "PyTools"}
    return TEMPLATES.TemplateResponse(request, "pages/privacy_policy.html", kwargs)
