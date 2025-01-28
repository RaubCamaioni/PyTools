from fastapi import Request, APIRouter, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from app.models import tools
from app.models.tools import SessionDep, User, FilterDep
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
    filter: FilterDep,
    id: int = None,
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

    db_tool: tools.Tool = tools.get_tool(session, id)

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
