from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.routing import Mount
from fastapi import FastAPI
from pathlib import Path

from app.models.tools import create_db_and_tables
from app.routes import tools, auth, upload, user
from app import logger, SECRET_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
APP_DIRECTORY = Path(__file__).parent
app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
app.mount("/scripts", StaticFiles(directory=APP_DIRECTORY / "scripts"), name="scripts")
app.mount("/webfonts", StaticFiles(directory=APP_DIRECTORY / "webfonts"), name="webfonts")
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(tools.router)
app.include_router(user.router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


for route in app.routes:
    if isinstance(route, Mount):
        continue
    logger.info(f"{route.methods} {route.path} {route.name}")
