from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from app.models import tools as db
from app.routes import admin as admin_routes
from app.routes.auth import current_user
from app import TEMPLATES, logger

router = APIRouter()


@router.get("/user", response_class=HTMLResponse)
async def user_page(request: Request, session: db.SessionDep):
    """The profile: the alias and the user's own tools; for an admin, every account and its tools below them."""
    user = current_user(request, session)
    alias = user.alias if user is not None else "anonymous"

    return TEMPLATES.TemplateResponse(
        request,
        "pages/user.html",
        {
            "header_title": f"Alias: {alias}",
            "alias": alias,
            "request": request,
            "root_path": request.scope.get("root_path"),
            "accounts": db.get_users_with_tools(session) if admin_routes.is_admin(request, session) else None,
        },
    )
