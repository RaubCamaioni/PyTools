"""Categories: up to three leaf paths from categories.yaml, the first being the tool's primary.

Only paths still in the tree count ("effective" categories); a tool with none, or whose paths the tree has
since dropped, belongs to Miscellaneous, so it never disappears from browsing.
"""

from typing import Mapping, Optional

from sqlalchemy import delete, exists, or_
from sqlmodel import Field, Session, SQLModel, select

from app import TEMPLATES, categories

MAX_CATEGORIES = 3

# the editor and display partials label paths and list the choices from the tree
TEMPLATES.env.globals.update(category_label=categories.label, category_leaves=categories.leaves)


class ToolCategory(SQLModel, table=True):
    tool_id: int = Field(foreign_key="tool.id", primary_key=True)
    path: str = Field(primary_key=True, index=True)
    position: int = Field(default=0)


def effective(paths: list[str]) -> list[str]:
    live = [path for path in paths if categories.is_leaf(path)]
    return live or [categories.MISC]


def tool_ids_in(paths: list[str]):
    """A subquery of the tool ids filed under any of `paths` by effective category."""
    from app.models.tools import Tool

    live = [path for path, _ in categories.leaves()]
    filed = select(ToolCategory.tool_id).where(ToolCategory.path.in_([p for p in paths if p in live]))
    conditions = [Tool.id.in_(filed)]
    if categories.MISC in paths:
        # misc also holds every tool without a live non-misc category
        real = [p for p in live if p != categories.MISC]
        conditions.append(~exists().where(ToolCategory.tool_id == Tool.id, ToolCategory.path.in_(real)))
    return select(Tool.id).where(or_(*conditions))


class Categories:
    key = "categories"
    editor_template = "components/meta_categories_editor.html"
    display_template = "components/meta_categories_display.html"

    def parse(self, form: Mapping[str, list[str]]) -> Optional[list[str]]:
        from app.metadata import MetadataError

        if f"{self.key}.present" not in form:
            return None
        paths = [value.strip() for value in form.get(self.key, []) if value.strip()]
        for path in paths:
            if not categories.is_leaf(path):
                valid = ", ".join(p for p, _ in categories.leaves())
                raise MetadataError(f"unknown category {path!r}; choose from: {valid}")
        if len(set(paths)) != len(paths):
            raise MetadataError("a category is listed twice (duplicate)")
        if len(paths) > MAX_CATEGORIES:
            raise MetadataError(f"at most {MAX_CATEGORIES} categories, got {len(paths)}")
        if categories.MISC in paths and len(paths) > 1:
            raise MetadataError("misc cannot be combined with other categories")
        return paths

    def delete(self, session: Session, tool_id: int) -> None:
        session.exec(delete(ToolCategory).where(ToolCategory.tool_id == tool_id))

    def save(self, session: Session, tool_id: int, value: list[str]) -> None:
        self.delete(session, tool_id)
        for position, path in enumerate(value):
            session.add(ToolCategory(tool_id=tool_id, path=path, position=position))

    def load(self, session: Session, tool_ids: list[int]) -> dict[int, list[str]]:
        stored: dict[int, list[str]] = {tool_id: [] for tool_id in tool_ids}
        if tool_ids:
            rows = session.exec(
                select(ToolCategory).where(ToolCategory.tool_id.in_(tool_ids)).order_by(ToolCategory.position)
            ).all()
            for row in rows:
                stored[row.tool_id].append(row.path)
        return {tool_id: effective(paths) for tool_id, paths in stored.items()}
