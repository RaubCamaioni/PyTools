from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware
from app.routes import tools, auth, upload
from app.models.tools import create_db_and_tables
from contextlib import asynccontextmanager
import os

SECRET_KEY = os.environ.get("SECRET_KEY") or None
if SECRET_KEY is None:
    raise Exception("Missing SECRET_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
APP_DIRECTORY = Path(__file__).parent
app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
app.mount("/scripts", StaticFiles(directory=APP_DIRECTORY / "scripts"), name="scripts")
app.include_router(auth.router)
app.include_router(tools.router)
app.include_router(upload.router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
