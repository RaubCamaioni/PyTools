from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from app.routes.auth import User
from app import TEMPLATES

router = APIRouter()


@router.get("/user", response_class=HTMLResponse)
async def user_page(request: Request):
    name = "Unknown"
    if "user" in request.session:
        user: User = User.model_validate_json(request.session.get("user"))
        name = user.alias

    return TEMPLATES.TemplateResponse(
        "pages/user.html",
        {
            "header_title": f"Alias: {name}",
            "request": request,
            "root_path": request.scope.get("root_path"),
        },
    )
