from fastapi import Depends, APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.config import Config
from authlib.integrations.starlette_client import OAuth
import jwt

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

config = Config(".env")
oauth = OAuth(config)
CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",
    },
)


@router.route("/login")
async def login(request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.post("/auth/google")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    if user:
        request.session["user"] = user
    return RedirectResponse(url="/")


@router.route("/logout")
async def logout(request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


# @router.post("/auth/google")
# async def auth_google(request: Request):
#     try:
#         access_token = await oauth.google.authorize_access_token(request)
#     except OAuthError as e:
#         print(f"Auth ERROR: {e}")
#         return RedirectResponse(url="/")
#     user_data = await oauth.google.parse_id_token(request, access_token)
#     print(user_data)
#     request.session["user"] = dict(user_data)
