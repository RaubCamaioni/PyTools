from fastapi import Depends, HTTPException
from typing import Annotated, Optional, Any
from profanityfilter import ProfanityFilter
import pyparsing as pp
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
import hashlib
import logging
import ast

from app import DATABASE

logger = logging.getLogger("uvicorn.error")

sqlite_url = f"sqlite:///{DATABASE}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


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
    only_public: bool = True,
) -> list[tuple[int, str]]:
    with session:
        conditions = []
        if only_public:
            conditions = [Tool.public == True]
        statement = (
            select(Tool.id, Tool.name)
            .where(*conditions)
            .offset(start)
            .limit(end - start)
        )
        return session.exec(statement).all()


def get_tools_by_tags(
    session: Session,
    tags: list[str],
    start: int,
    end: int,
    only_public: bool = True,
) -> list[Tool]:
    with session:
        conditions = [Tool.tags.ilike(f"%{tag}%") for tag in tags]
        if only_public:
            conditions.append(Tool.public == True)
        statement = (
            select(Tool.id, Tool.name)
            .where(*conditions)
            .offset(start)
            .limit(end - start)
        )
        return session.exec(statement).all()


def get_user_tools(session: Session, user: User) -> list[Tool]:
    statement = select(Tool).where(Tool.user_id == user.id)
    result = session.exec(statement).all()
    return list(result)


def add_tool(session: Session, tool: Tool):
    session.add(tool)
    session.commit()


def get_tool(session: Session, id: Optional[int]):
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
    conditions = [Tool.id == tool_id]
    statement = select(Tool).where(*conditions)
    result = session.exec(statement).first()
    return result


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
    except SyntaxError as e:
        detail = f"Python Syntax Error: line {e.lineno}"
        raise HTTPException(status_code=400, detail=detail)

    try:
        entry_node = next(filter(lambda n: n.name == tool_name, FunctionVisitor(tree)))
    except StopIteration:
        detail = "Entrypoint Not Found: entrypoint function matching file name missing"
        raise HTTPException(status_code=400, detail=detail)

    defaults = [None] * len(entry_node.args.args)
    for i, node in enumerate(entry_node.args.defaults[::-1]):
        default = ast.unparse(node)

        if default[0] in ['"', "'"] and len(default) >= 2:
            default = default[1:-1]

        defaults[-(i + 1)] = default

    arguments = {}
    for arg, default in zip(entry_node.args.args, defaults):
        if not arg.annotation:
            detail = "Annotation Error: arguments to entrypoint function must have annotations"
            raise HTTPException(status_code=400, detail=detail)
        arguments[arg.arg] = (ast.unparse(arg.annotation), default)

    return arguments


def create_tool(user_id: int, tool_name: str, tool_source: str) -> Tool:
    tags = get_tags(tool_source.split("\n")[0])
    tags.append(tool_name)
    arguments = get_arguments(tool_name, tool_source)

    return Tool(
        name=tool_name,
        code=tool_source,
        arguments=arguments,
        user_id=user_id,
        tags=tags,
    )
