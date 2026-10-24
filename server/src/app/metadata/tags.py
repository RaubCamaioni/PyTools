"""Tags: free-form search words. Normalised so that "Kitchen Tools" and "kitchen-tools" are one tag, and
suggested from the tags already in use so authors reuse them instead of inventing near-duplicates."""

from functools import lru_cache
from typing import Mapping, Optional
import re

from sqlalchemy import delete, func
from sqlmodel import Field, Session, SQLModel, select

MAX_TAGS = 10
TAG = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,29}$")


class ToolTag(SQLModel, table=True):
    tool_id: int = Field(foreign_key="tool.id", primary_key=True)
    tag: str = Field(primary_key=True, index=True)
    position: int = Field(default=0)


@lru_cache(maxsize=1)
def _profanity():
    from app.models.tools import get_filter

    return next(get_filter())


def normalise(raw: str) -> str:
    from app.metadata import MetadataError

    tag = re.sub(r"\s+", "-", raw.strip().lower())
    if not TAG.match(tag):
        raise MetadataError(
            f"tag {raw.strip()!r}: use 1 to 30 letters, digits, '.', '+' or '-', starting with a letter or digit"
        )
    if not _profanity().is_clean(tag.replace("-", " ")):
        raise MetadataError(f"tag {raw.strip()!r} is blocked by the profanity filter")
    return tag


def escape_like(text: str) -> str:
    """`text` for a LIKE pattern with ESCAPE '\\': its % and _ match themselves."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def suggest(session: Session, prefix: str, limit: Optional[int] = 10) -> list[tuple[str, int]]:
    """Tags on public tools starting with `prefix`, most used first; `limit=None` for all of them."""
    from app.models.tools import Tool

    count = func.count(ToolTag.tool_id)
    statement = (
        select(ToolTag.tag, count)
        .join(Tool, Tool.id == ToolTag.tool_id)
        .where(Tool.public == True)  # noqa: E712
        .where(ToolTag.tag.like(escape_like(prefix.strip().lower()) + "%", escape="\\"))
        .group_by(ToolTag.tag)
        .order_by(count.desc(), ToolTag.tag)
        .limit(limit)
    )
    return [(tag, n) for tag, n in session.exec(statement).all()]


class Tags:
    key = "tags"
    editor_template = "components/meta_tags_editor.html"
    display_template = "components/meta_tags_display.html"

    def parse(self, form: Mapping[str, list[str]]) -> Optional[list[str]]:
        from app.metadata import MetadataError

        if f"{self.key}.present" not in form:
            return None
        tags: list[str] = []
        for value in form.get(self.key, []):
            for raw in value.split(","):
                if raw.strip():
                    tag = normalise(raw)
                    if tag not in tags:
                        tags.append(tag)
        if len(tags) > MAX_TAGS:
            raise MetadataError(f"at most {MAX_TAGS} tags, got {len(tags)}")
        return tags

    def delete(self, session: Session, tool_id: int) -> None:
        session.exec(delete(ToolTag).where(ToolTag.tool_id == tool_id))

    def save(self, session: Session, tool_id: int, value: list[str]) -> None:
        self.delete(session, tool_id)
        for position, tag in enumerate(value):
            session.add(ToolTag(tool_id=tool_id, tag=tag, position=position))

    def load(self, session: Session, tool_ids: list[int]) -> dict[int, list[str]]:
        loaded: dict[int, list[str]] = {tool_id: [] for tool_id in tool_ids}
        if tool_ids:
            rows = session.exec(
                select(ToolTag).where(ToolTag.tool_id.in_(tool_ids)).order_by(ToolTag.position)
            ).all()
            for row in rows:
                loaded[row.tool_id].append(row.tag)
        return loaded
