from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from app.routes.auth import User
from app import TEMPLATES, logger

router = APIRouter()


@router.get("/user", response_class=HTMLResponse)
async def user_page(request: Request):
    alias = "anonymous"

    if "user" in request.session:
        user: User = User.model_validate_json(request.session["user"])
        alias = user.alias

    return TEMPLATES.TemplateResponse(
        "pages/user.html",
        {
            "header_title": f"Alias: {alias}",
            "alias": alias,
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )
