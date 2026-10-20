"""Admin page: every account and its tools, with a ban switch per account.

Who is an admin is a column on the user table (`user.admin`), set in the database; nothing
in the code names an account. Non-admins get a 404, like a private tool.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app import TEMPLATES
from app.models import tools as db
from app.routes.auth import session_user

router = APIRouter()


def require_admin(request: Request) -> db.User:
    user = session_user(request)
    if user is None or not user.admin:
        raise HTTPException(status_code=404, detail="Not Found")
    return user


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, session: db.SessionDep):
    require_admin(request)
    return TEMPLATES.TemplateResponse(
        request,
        "pages/admin.html",
        {
            "header_title": "PyTools",
            "request": request,
            "root_path": request.scope.get("root_path"),
            "accounts": db.get_users_with_tools(session),
        },
    )


@router.post("/admin/ban/{user_id}", response_class=HTMLResponse)
async def ban_user(request: Request, user_id: int, banned: bool, session: db.SessionDep):
    admin = require_admin(request)
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot ban yourself")
    db.set_banned(session, user_id, banned)
    return HTMLResponse(status_code=200)
