from fastapi import Request, APIRouter, UploadFile
from fastapi.responses import HTMLResponse
from app.models import tools
from app.models.tools import SessionDep, User
from pathlib import Path
from app import TEMPLATES, logger


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
    id: int = None,
):
    if "user" not in request.session:
        return HTMLResponse(status_code=404)

    user: User = User.model_validate_json(request.session["user"])

    name = file.filename
    if name is None:
        return HTMLResponse(status_code=404)

    code = await file.read()

    db_tool = tools.get_tool(session, id)

    if db_tool is None:
        tool = tools.create_tool(user.id, Path(name).stem, code.decode())
        if tool is None:
            return HTMLResponse(status_code=404)
        session.add(tool)
        session.commit()

    else:
        tool = tools.create_tool(user.id, Path(name).stem, code.decode())
        db_tool.code = tool.code
        session.commit()

    return HTMLResponse(status_code=200)
