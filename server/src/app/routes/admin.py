"""Admin actions: ban and unban an account. An admin's own profile (/user) lists every account and its tools.

Who is an admin is a column on the user table (`user.admin`), set in the database; nothing
in the code names an account. Non-admins get a 404, like a private tool.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.models import tools as db
from app.routes.auth import session_user

router = APIRouter()


def is_admin(request: Request) -> bool:
    user = session_user(request)
    return user is not None and user.admin


def require_admin(request: Request) -> db.User:
    if not is_admin(request):
        raise HTTPException(status_code=404, detail="Not Found")
    return session_user(request)


@router.get("/admin")
async def admin_page(request: Request):
    """The admin page became part of the profile: old links and bookmarks land there."""
    return RedirectResponse(f"{request.scope.get('root_path', '')}/user", status_code=301)


@router.post("/admin/ban/{user_id}", response_class=HTMLResponse)
async def ban_user(request: Request, user_id: int, months: int, session: db.SessionDep):
    """Ban for 1, 6 or 12 months: the account cannot log in and all its tools go private."""
    admin = require_admin(request)
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot ban yourself")
    if months not in db.BAN_PERIODS_MONTHS:
        raise HTTPException(status_code=400, detail="Ban period must be 1, 6 or 12 months")
    db.set_banned(session, user_id, months)
    return HTMLResponse(status_code=200)


@router.post("/admin/unban/{user_id}", response_class=HTMLResponse)
async def unban_user(request: Request, user_id: int, session: db.SessionDep):
    require_admin(request)
    db.set_banned(session, user_id, None)
    return HTMLResponse(status_code=200)
