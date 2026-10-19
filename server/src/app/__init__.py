from fastapi.templating import Jinja2Templates
from pathlib import Path
import string
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from app.utility.sandbox_config import SandboxConfig


REQUIRED_ENVIRONMENT = ("SESSION_KEY", "DATABASE")


@dataclass
class _ENVIRONMENT:
    SESSION_KEY: str = os.environ.get("SESSION_KEY")
    DATABASE: str = os.environ.get("DATABASE")
    # GitHub login is optional: without the keys the site runs with login disabled
    GITHUB_CLIENT_ID: Optional[str] = os.environ.get("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.environ.get("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI: str = os.environ.get("GITHUB_REDIRECT_URI", "https://pywebtools.com/auth/github")
    # the GitHub account that owns the tools uploaded under the original (Google) account
    OWNER_GITHUB_LOGIN: str = os.environ.get("OWNER_GITHUB_LOGIN", "RaubCamaioni")
    # SANDBOX_* variables all have defaults; see SandboxConfig
    sandbox: SandboxConfig = field(default_factory=lambda: SandboxConfig.from_environment(os.environ))

    def __post_init__(self):
        for name in REQUIRED_ENVIRONMENT:
            if getattr(self, name) is None:
                raise ValueError(f"Missing environment variable: {name}")


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
