from fastapi import Request, APIRouter, UploadFile, Query
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from app.models import tools
from app.routes import tools as tools_routes
from sandboxcore.host import SandboxBusy, SandboxUnavailable, SignatureError, Source, SourceError, accept_source
from sandboxcore.source import MAX_CODE_BYTES
from app.models.tools import SessionDep, User, FilterDep, get_user, lift_expired_ban
from app.routes.auth import session_user
from app import TEMPLATES, logger
from typing import Optional
from urllib.parse import parse_qsl

router = APIRouter()


@router.delete("/manage/tool/delete/{id}", response_class=HTMLResponse)
async def tool_delete(
    request: Request,
    id: int,
    session: SessionDep,
):
    user = session_user(request)
    if user is None:
        logger.info("user is not logged in")
        return HTMLResponse(status_code=407)

    tool = tools.get_tool(session, id)
    if tool is None:
        logger.info("unable to find tool")
        return HTMLResponse(status_code=404)

    # the owner, or an admin removing an offending upload
    if user.id != tool.user_id and not user.admin:
        logger.info("tool does not belong to user")
        return HTMLResponse(status_code=404)

    tools.del_tool(session, tool)
    return HTMLResponse(status_code=200)


@router.get("/manage/tool/upload", response_class=HTMLResponse)
async def tool_upload_get(request: Request):
    return TEMPLATES.TemplateResponse(
        request,
        "pages/upload.html",
        {
            "header_title": "upload",
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )


@router.post("/manage/tool/upload", response_class=HTMLResponse)
@router.post("/manage/tool/update/{id}", response_class=HTMLResponse)
async def tool_upload_post(
    request: Request,
    file: UploadFile,
    session: SessionDep,
    filter: FilterDep,
    id: Optional[int] = None,
):
    session_account = session_user(request)
    if session_account is None:
        raise HTTPException(status_code=404, detail="Uploading code requires login.")
    # bans and roles are read from the database: the cookie only says who is logged in
    user: User = get_user(session, session_account.id)
    lift_expired_ban(session, user)
    if user.banned:
        raise HTTPException(status_code=403, detail="This account is banned.")

    name = file.filename
    if name is None:
        raise HTTPException(status_code=400, detail="Upload filename required.")

    # read at most one byte past the limit: accept_source refuses anything larger
    data = await file.read(MAX_CODE_BYTES + 1)
    try:
        source = accept_source(data, name)
    except SourceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    clean = filter.is_clean(source.code)
    if not clean:
        raise HTTPException(status_code=400, detail="Blocked by profanity filter.")

    db_tool: Optional[tools.Tool] = tools.get_tool(session, id)

    # only the owner replaces a tool's code; an admin removes an offending tool instead
    if db_tool is not None and db_tool.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tool does not exist.")

    if db_tool is None:
        tool = await _create_tool(user.id, source)
        if tool is None:
            raise HTTPException(status_code=404, detail="Error creating tool.")
        session.add(tool)
        session.commit()

    else:
        tool = await _create_tool(user.id, source)
        if tool is None:
            raise HTTPException(status_code=404, detail="Error updating tool.")
        db_tool.name = tool.name
        db_tool.code = tool.code
        db_tool.arguments = tool.arguments
        session.commit()

    return HTMLResponse(status_code=200)


async def _create_tool(user_id: int, source: Source) -> tools.Tool:
    """Prepare the code, read its signature in the sandbox (never parsed here), and build the tool."""
    source = tools.prepare_source(source)
    try:
        signature = await tools_routes.sandbox.inspect(source)
    except (SignatureError, SourceError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SandboxBusy:
        raise HTTPException(status_code=503, detail="Server busy, try again")
    except SandboxUnavailable:
        raise HTTPException(status_code=503, detail="Sandbox unavailable")
    return tools.create_tool(user_id, source, signature)


@router.post("/manage/user/settings", response_class=HTMLResponse)
async def user_settings(
    request: Request,
    session: SessionDep,
):
    if "user" not in request.session:
        raise HTTPException(status_code=404, detail="Requires Login.")
    user: User = User.model_validate_json(request.session["user"])
    user: User = get_user(session, user.id)

    form_data = await request.form()

    if "alias" in form_data:
        user.alias = str(form_data["alias"])

    # update session and database
    request.session["user"] = user.model_dump_json()
    session.commit()

    return HTMLResponse(status_code=200)


@router.post("/manage/tool/settings/{id}", response_class=HTMLResponse)
async def tool_set_public(
    request: Request,
    session: SessionDep,
    id: int,
    public: Optional[bool] = None,
    anonymous: Optional[bool] = None,
):
    if "user" not in request.session:
        raise HTTPException(status_code=404, detail="Requires login.")
    user: User = User.model_validate_json(request.session["user"])

    db_tool: Optional[tools.Tool] = tools.get_tool(session, id)

    # only the owner replaces a tool's code; an admin removes an offending tool instead
    if db_tool is not None and db_tool.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tool does not exist.")

    if db_tool is None:
        raise HTTPException(status_code=404, detail="Tool does not exist.")

    if db_tool.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tool owner does not match user.")

    if public is not None:
        db_tool.public = public

    if anonymous is not None:
        db_tool.annonymous = anonymous

    session.commit()
    return HTMLResponse(status_code=200)
