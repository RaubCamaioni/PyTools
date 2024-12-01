from fastapi import FastAPI, HTTPException, Request, APIRouter, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.models.tools import SessionDep, create_tool, User, Tool, add_tool
from pathlib import Path

TEMPLATES = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/manage/tool/upload", response_class=HTMLResponse)
async def tool_upload_get(request: Request):
    return TEMPLATES.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )


@router.post("/manage/tool/upload", response_class=HTMLResponse)
async def tool_upload_post(request: Request, file: UploadFile, session: SessionDep):
    if "user" not in request.session:
        return HTMLResponse(status_code=404)

    user: User = User.model_validate_json(request.session["user"])

    name = file.filename
    if name is None:
        return HTMLResponse(status_code=404)

    code = await file.read()

    tool = create_tool(user.id, Path(name).stem, code.decode())
    if tool is None:
        return HTMLResponse(status_code=404)

    add_tool(session, tool)

    return HTMLResponse(status_code=200)


@router.get("/manage/tool/delete", response_class=JSONResponse)
async def tool_delete(request: Request, session: SessionDep):
    pass
