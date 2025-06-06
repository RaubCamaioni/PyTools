from fastapi import Request, APIRouter, UploadFile, Query
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from app.models import tools
from app.models.tools import SessionDep, User, FilterDep, get_user
from pathlib import Path
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
    if "user" not in request.session:
        logger.info("user is not logged in")
        return HTMLResponse(status_code=407)

    tool = tools.get_tool(session, id)
    if tool is None:
        logger.info("unable to find tool")
        return HTMLResponse(status_code=404)

    user: User = User.model_validate_json(request.session["user"])

    if user.id != tool.user_id:
        logger.info("tool does not belong to user")
        return HTMLResponse(status_code=404)

    tools.del_tool(session, tool)
    return HTMLResponse(status_code=200)


@router.get("/manage/tool/upload", response_class=HTMLResponse)
async def tool_upload_get(request: Request):
    return TEMPLATES.TemplateResponse(
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
    if "user" not in request.session:
        raise HTTPException(status_code=404, detail="Uploading code requires login.")
    user: User = User.model_validate_json(request.session["user"])

    name = file.filename
    if name is None:
        raise HTTPException(status_code=400, detail="Upload filename required.")

    code = await file.read()

    clean = filter.is_clean(code.decode())
    if not clean:
        raise HTTPException(status_code=400, detail="Blocked by profanity filter.")

    db_tool: Optional[tools.Tool] = tools.get_tool(session, id)

    if db_tool is None:
        tool = tools.create_tool(user.id, Path(name).stem, code.decode())
        if tool is None:
            raise HTTPException(status_code=404, detail="Error creating tool.")
        session.add(tool)
        session.commit()

    else:
        tool = tools.create_tool(user.id, Path(name).stem, code.decode())
        if tool is None:
            return HTTPException(status_code=404, detail="Error updating tool.")
        db_tool.name = tool.name
        db_tool.code = tool.code
        db_tool.arguments = tool.arguments
        db_tool.tags = tool.tags
        session.commit()

    return HTMLResponse(status_code=200)


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
