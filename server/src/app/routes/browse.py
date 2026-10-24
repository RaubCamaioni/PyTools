"""Browsing by category. /c/<category> lists the public tools filed under any of its subcategories,
/c/<category>/<subcategory> one leaf, /c/misc everything unfiled. The pages are the front page with a
breadcrumb, the category's description, and its search and list scoped to the category."""

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlmodel import Session, select

from app import TEMPLATES, categories
from app.metadata.categories import tool_ids_in
from app.models.tools import SessionDep, Tool

router = APIRouter()


def normalise_kind(value: Optional[str]) -> Optional[str]:
    """The view a request asks for: "model" (only tools returning a CadQuery object), "script" (every other tool:
    converters, calculators, text tools) or None (every tool)."""
    return value if value in ("model", "script") else None


def category_counts(session: Session, kind: Optional[str] = None) -> dict[str, int]:
    """Public tools (of `kind`, if given) per leaf path and per top-level slug; a tool counts once in each place it
    is filed."""

    def count(paths: list[str]) -> int:
        conditions = [Tool.public == True, Tool.id.in_(tool_ids_in(paths))]  # noqa: E712
        if kind is not None:
            conditions.append(Tool.kind == kind)
        return session.exec(select(func.count(Tool.id)).where(*conditions)).one()

    counts = {}
    for category in categories.TREE:
        under = categories.paths_under(category.slug)
        counts[category.slug] = count(under)
        for path in under:
            counts[path] = count([path]) if path != category.slug else counts[category.slug]
    return counts


def category_bar(session: Session, current: Optional[str], kind: Optional[str] = None) -> list[dict]:
    """The front page's tree: the categories with something in them in this view, with counts and their non-empty
    subcategories; the current one is open (and shown even when empty)."""
    counts = category_counts(session, kind)
    top = current.split("/")[0] if current is not None else None
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "count": counts[c.slug],
            "open": top == c.slug,
            "subs": [
                {"path": s.path, "name": s.name, "count": counts[s.path]}
                for s in c.subcategories
                if counts[s.path] or s.path == current
            ],
        }
        for c in categories.TREE
        if counts[c.slug] or c.slug == top
    ]


def index_page(
    request: Request, session: Session, category: Optional[str] = None, search: str = "", kind: Optional[str] = None
):
    """The front page; with `category`, that category's page (callers check it exists); with kind "model", only
    the models, as cards; with kind "script", only the rest."""
    kind = normalise_kind(kind)
    crumbs, description = [], ""
    if category is not None:
        top, _, sub = category.partition("/")
        view = f"?kind={kind}" if kind else ""
        crumbs = [(categories.find(top).name, f"/c/{top}{view}")]
        if sub:
            crumbs.append((categories.find(category).name, f"/c/{category}{view}"))
        description = categories.find(category).description
    return TEMPLATES.TemplateResponse(
        request,
        "pages/index.html",
        {
            "header_title": "PyTools",
            "request": request,
            "root_path": request.scope.get("root_path"),
            "search": search,
            "category": category,
            "crumbs": crumbs,
            "description": description,
            "bar": category_bar(session, category, kind),
            "kind": kind,
        },
    )


@router.get("/c/{category}", response_class=HTMLResponse)
async def category_page(request: Request, category: str, session: SessionDep, search: str = "", kind: str = ""):
    if "/" in category or categories.find(category) is None:
        raise HTTPException(status_code=404, detail="Category Not Found")
    return index_page(request, session, category, search, kind)


@router.get("/c/{category}/{subcategory}", response_class=HTMLResponse)
async def subcategory_page(
    request: Request, category: str, subcategory: str, session: SessionDep, search: str = "", kind: str = ""
):
    path = f"{category}/{subcategory}"
    if not categories.is_leaf(path):
        raise HTTPException(status_code=404, detail="Category Not Found")
    return index_page(request, session, path, search, kind)
