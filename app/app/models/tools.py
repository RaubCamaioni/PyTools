from typing import Annotated, Optional, Any
from fastapi import Depends, FastAPI, HTTPException, Query
import hashlib
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


def hash_id(id: str) -> int:
    return int(hashlib.sha256(id.encode()).hexdigest(), 16) % 10**8


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    alias: str = Field(default="annonymous")

    def __init__(self, **data: Any):
        if "id" in data and isinstance(data["id"], str):
            data["id"] = (
                int(hashlib.sha256(data["id"].encode()).hexdigest(), 16) % 10**8
            )
        super().__init__(**data)


class Tool(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int
    tool_name: str
    code: str | None = Field(default=None)
    tags: list[str] = Field(sa_column=Column(JSON))
    public: bool = Field(default=False)
    annonymous: bool = Field(default=True)


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
