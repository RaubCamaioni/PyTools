from fastapi.templating import Jinja2Templates
from pathlib import Path
import string
import logging
import os
from dataclasses import dataclass, field

from app.utility.sandbox_config import SandboxConfig


@dataclass
class _ENVIRONMENT:
    SESSION_KEY: str = os.environ.get("SESSION_KEY")
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI")
    DATABASE: str = os.environ.get("DATABASE")
    # SANDBOX_* variables all have defaults; see SandboxConfig
    sandbox: SandboxConfig = field(default_factory=lambda: SandboxConfig.from_environment(os.environ))

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


def _static_version() -> str:
    """Content hash of the built stylesheet: browsers re-fetch /static/*.css?v=... after every release."""
    import hashlib

    try:
        css = (APP_DIRECTORY / "webapp" / "static" / "output.css").read_bytes()
    except OSError:
        return "0"
    return hashlib.sha256(css).hexdigest()[:12]


TEMPLATES.env.globals["static_version"] = _static_version()

logger = logging.getLogger("uvicorn.error")
