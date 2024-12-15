from fastapi.templating import Jinja2Templates
from pathlib import Path
import string
import logging

ALLOWED_CHARACTERS = string.ascii_letters + string.digits + "-_"
APP_DIRECTORY = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("uvicorn.error")
