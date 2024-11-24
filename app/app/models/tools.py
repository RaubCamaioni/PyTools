from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str | None = Field(default=None)
    verified_email: str | None = Field(default=None)
    name: str | None = Field(default=None)
    given_name: str | None = Field(default=None)
    family_name: str | None = Field(default=None)
    picture: str | None = Field(default=None)

class Tool(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

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