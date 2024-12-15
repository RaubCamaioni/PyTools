from typing import Annotated, Optional, Any
from fastapi import Depends, FastAPI, HTTPException, Query
from typing import List, Dict, Type, Literal, get_origin, Annotated, Any
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
    upvotes: int = Field(default=0)
    downvotes: int = Field(default=0)
    usage: int = Field(default=0)
    public: bool = Field(default=False)
    annonymous: bool = Field(default=True)
    user_id: int = Field(default=None, foreign_key="user.id")
    user: User = Relationship(back_populates="tools")


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


def get_tools(session: Session) -> list[tuple[int, str]]:
    with Session(engine) as session:
        statement = select(Tool.id, Tool.name)
        result = session.exec(statement)
        return list(result)


def get_user_tools(session: Session, user: User) -> list[tuple[int, str]]:
    with Session(engine) as session:
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
    with Session(engine) as session:
        statement = select(Tool).where(Tool.id == tool_id)
        result = session.exec(statement).first()
        return result


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: ast.Module):
        self.nodes: list[ast.FunctionDef] = []
        self.visit(module)

    def visit_FunctionDef(self, node):
        self.nodes.append(node)
        self.generic_visit(node)

    def __iter__(self):
        return iter(self.nodes)


def create_tool(user_id: int, tool_name: str, tool_source: str) -> Tool:
    try:
        tree = ast.parse(tool_source)
    except SyntaxError:
        logger.info("Upload Code: Syntax Error")
        return None

    entry_node = None
    for node in FunctionVisitor(tree):
        if tool_name == node.name:
            entry_node = node

    if entry_node is None:
        logger.warning(f"no entrypoint found in: {tool_name}")
        return None

    arguments = {}

    defaults = [None] * len(entry_node.args.args)
    for i, default in enumerate(entry_node.args.defaults[::-1]):
        defaults[-i - 1] = ast.unparse(default)

    for arg, default in zip(entry_node.args.args, defaults):
        if not arg.annotation:
            logger.warning(f"{tool_name} arguments must be annotated")
            return None
        name = arg.arg
        type = ast.unparse(arg.annotation)
        arguments[name] = (type, default)

    # debug
    # tool_arg_string = []
    # for name, (type, default) in arguments.items():
    #     tool_arg_string.append(f"  {name}: {type}")
    # tool_arg_string = "\n".join(tool_arg_string)
    # logger.info(f"Loading Tool: {tool_name}\n{tool_arg_string}")

    return Tool(
        name=tool_name,
        code=tool_source,
        arguments=arguments,
        user_id=user_id,
    )
