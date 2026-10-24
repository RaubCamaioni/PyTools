"""Editing a tool's metadata (tags, categories, later kinds) and suggesting tags already in use.

Only the tool's owner or an admin may edit; anyone else gets a 404, as for code updates. The routes go
through the metadata registry, so a new kind needs no change here.
"""

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse

from app import metadata
from app.metadata.tags import suggest
from app.models import tools
from app.models.tools import SessionDep, get_user, lift_expired_ban
from app.routes.auth import session_user
from app.utility import render

router = APIRouter()

# the most tags the dropdown lists when nothing is typed (the whole list, browsed by scrolling)
BROWSE_LIMIT = 500


def can_edit(request: Request, session, tool: tools.Tool) -> bool:
    account = session_user(request)
    if account is None:
        return False
    user = get_user(session, account.id)  # admin and banned are read from the database, never the cookie
    lift_expired_ban(session, user)
    if user.banned:
        return False
    return tool.user_id == user.id or user.admin


def _tool(session, id: int) -> tools.Tool:
    tool: Optional[tools.Tool] = tools.get_tool(session, id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool Not Found")
    return tool


def _editable(request: Request, session, id: int) -> tools.Tool:
    tool = _tool(session, id)
    if not can_edit(request, session, tool):
        raise HTTPException(status_code=404, detail="Tool Not Found")
    return tool


def display(request: Request, session, tool: tools.Tool) -> str:
    values = metadata.load_all(session, [tool.id])[tool.id]
    return render.tool_meta(request.scope.get("root_path"), tool.id, values)


@router.get("/manage/tool/create", response_class=HTMLResponse)
async def create_dialog(request: Request, session: SessionDep):
    """The profile's [create]: the empty dialog."""
    if session_user(request) is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return HTMLResponse(render.tool_dialog(request.scope.get("root_path"), None, None, {}))


@router.get("/manage/tool/{id}/edit", response_class=HTMLResponse)
async def edit_dialog(request: Request, id: int, session: SessionDep):
    """A row's [edit]: the dialog filled with the tool's metadata (owner or admin)."""
    tool = _editable(request, session, id)
    values = metadata.load_all(session, [tool.id])[tool.id]
    return HTMLResponse(render.tool_dialog(request.scope.get("root_path"), tool.id, tool.name, values))


@router.get("/tags/suggest")
async def tag_suggestions(session: SessionDep, q: str = ""):
    """The tag editor's dropdown: tags in use on public tools that start with `q`, most used first; every
    tag in use (up to BROWSE_LIMIT) when nothing is typed, so the list can be browsed."""
    limit = 50 if q.strip() else BROWSE_LIMIT
    return [{"tag": tag, "count": count} for tag, count in suggest(session, q, limit)]
