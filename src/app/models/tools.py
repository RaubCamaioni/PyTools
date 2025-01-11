from typing import Annotated, Optional, Any
from fastapi import Depends, FastAPI, HTTPException, Query
from typing import List, Dict, Type, Literal, get_origin, Annotated, Any
from profanityfilter import ProfanityFilter
import pyparsing as pp
import hashlib
import ast
from pathlib import Path
import logging
from app.utility import render
from sqlmodel import (
    Field,
    Session,
    SQLModel,
    create_engine,
    select,
    Relationship,
    JSON,
    Column,
)

logger = logging.getLogger("uvicorn.error")


def hash_id(id: str) -> int:
    return int(hashlib.sha256(id.encode()).hexdigest(), 16) % 10**8


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    alias: str = Field(default="annonymous")
    tools: Optional[list["Tool"]] = Relationship(back_populates="user")

    def __init__(self, **data: Any):
        if "id" in data and isinstance(data["id"], str):
            data["id"] = hash_id(data["id"])

        super().__init__(**data)


class Tool(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    code: str
    arguments: dict[str, tuple[str, str]] = Field(default={}, sa_column=Column(JSON))
    tags: list[str] = Field(default={}, sa_column=Column(JSON))
    up_votes: list["UpVote"] = Relationship(back_populates="tool")
    down_votes: list["DownVote"] = Relationship(back_populates="tool")
    reports: list["Report"] = Relationship(back_populates="tool")
    usage: int = Field(default=0)
    # fails: int = Field(default=0)
    public: bool = Field(default=False)
    annonymous: bool = Field(default=True)
    user_id: int = Field(default=None, foreign_key="user.id")
    user: User = Relationship(back_populates="tools")


class UpVote(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tool_id: int = Field(foreign_key="tool.id")
    tool: Tool = Relationship(back_populates="up_votes")


class DownVote(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tool_id: int = Field(foreign_key="tool.id")
    tool: Tool = Relationship(back_populates="down_votes")


class Report(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tool_id: int = Field(foreign_key="tool.id")
    tool: Tool = Relationship(back_populates="reports")
    reason: str


def get_user(session: Session, id: int) -> User:
    statement = select(User).where(User.id == id)
    existing_user = session.exec(statement).first()

    if existing_user:
        return existing_user
    else:
        new_user = User(id=id)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user


def get_tools_by_index(
    session: Session,
    start: int,
    end: int,
) -> list[tuple[int, str]]:
    with session:
        statement = select(Tool.id, Tool.name).offset(start).limit(end - start)
        return session.exec(statement).all()


def get_tools_by_tags(
    session: Session,
    tags: list[str],
    start: int,
    end: int,
) -> list[Tool]:
    with session:
        # TODO: check speed
        conditions = [Tool.tags.like(f'%"{tag}"%') for tag in tags]
        statement = select(Tool.id, Tool.name).where(*conditions).offset(start).limit(end - start)
        return session.exec(statement).all()


def get_user_tools(session: Session, user: User) -> list[tuple[int, str]]:
    statement = select(Tool.id, Tool.name).where(Tool.user_id == user.id)
    result = session.exec(statement).all()
    return list(result)


def add_tool(session: Session, tool: Tool):
    session.add(tool)
    session.commit()


def get_tool(session: Session, id: int):
    statement = select(Tool).where(Tool.id == id)
    result = session.exec(statement)
    return result.first()


def del_tool(session: Session, tool: Tool):
    if not tool:
        return False
    session.delete(tool)
    session.commit()
    return True


def get_tool_by_id(session: Session, tool_id: int) -> Tool | None:
    statement = select(Tool).where(Tool.id == tool_id)
    result = session.exec(statement).first()
    return result


sqlite_file_name = "/data/database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def get_filter():
    pf = ProfanityFilter()
    yield pf


SessionDep = Annotated[Session, Depends(get_session)]
FilterDep = Annotated[ProfanityFilter, Depends(get_filter)]


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: ast.Module):
        self.nodes: list[ast.FunctionDef] = []
        self.visit(module)

    def visit_FunctionDef(self, node):
        self.nodes.append(node)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self.nodes)


def get_tags(tool_source: str) -> list[str]:
    word = pp.Word(pp.alphanums)
    tag = word + pp.Optional(pp.Suppress(pp.Literal(",")))
    comment_line = pp.Suppress(pp.Literal("#")) + pp.OneOrMore(tag)
    try:
        result = comment_line.parseString(tool_source)
        return list(result)
    except pp.ParseException:
        return []


def get_arguments(tool_name: str, tool_source: str) -> dict[str, str]:
    try:
        tree = ast.parse(tool_source)
    except SyntaxError:
        raise HTTPException(status_code=400, detail="python syntax error")

    try:
        entry_node = next(filter(lambda n: n.name == tool_name, FunctionVisitor(tree)))
    except StopIteration:
        raise HTTPException(status_code=400, detail="entrypoint not found")

    defaults = [None] * len(entry_node.args.args)
    for i, node in enumerate(entry_node.args.defaults[::-1]):
        defaults[-(i + 1)] = ast.unparse(node)

    arguments = {}
    for arg, default in zip(entry_node.args.args, defaults):
        if not arg.annotation:
            raise HTTPException(status_code=400, detail="annotated are required")
        arguments[arg.arg] = (ast.unparse(arg.annotation), default)

    return arguments


def create_tool(user_id: int, tool_name: str, tool_source: str) -> Tool:
    tags = get_tags(tool_source.split("\n")[0])
    arguments = get_arguments(tool_name, tool_source)

    return Tool(
        name=tool_name,
        code=tool_source,
        arguments=arguments,
        user_id=user_id,
        tags=tags,
    )
