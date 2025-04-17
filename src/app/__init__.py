from fastapi.templating import Jinja2Templates
from pathlib import Path
import string
import logging
import os
from dataclasses import dataclass


@dataclass
class _ENVIRONMENT:
    SESSION_KEY: str = os.environ.get("SESSION_KEY")
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI")
    DATABASE: str = os.environ.get("DATABASE")
    SANDBOX: str = os.environ.get("SANDBOX")

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if value is None:
                raise ValueError(f"Missing environment variable: {name}")

    @property
    def LOGIN_URL(self):
        return f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={self.GOOGLE_CLIENT_ID}&redirect_uri={self.GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=online"


ENVIRONMENT = _ENVIRONMENT()

ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "-_"
APP_DIRECTORY = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=APP_DIRECTORY / "webapp" / "templates")

logger = logging.getLogger("uvicorn.error")
