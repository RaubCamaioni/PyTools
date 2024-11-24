from fastapi import Depends, APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
import requests
import jwt
import os

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
LOGIN_URL = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=online"
TEMPLATES = Jinja2Templates(directory="app/templates")


@router.get("/login/button", response_class=HTMLResponse)
async def login_button(request: Request):
    logged = "user" in request.session

    if logged:
        user = request.session.get("user")
        name = user.get("name")
        kwargs = {"request": request, "name": name}
        button_html = TEMPLATES.TemplateResponse("logout_button.html", kwargs)
    else:
        kwargs = {"request": request, "url": LOGIN_URL}
        button_html = TEMPLATES.TemplateResponse("login_button.html", kwargs)

    return button_html


@router.post("/logout/button", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    kwargs = {"request": request, "url": LOGIN_URL}
    button_html = TEMPLATES.TemplateResponse("login_button.html", kwargs)
    return button_html


@router.get("/auth/google")
async def auth_google(request: Request, code: str):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)

    if response.status_code != 200:
        return HTTPException(status_code=403, detail="Access denied")

    access_token = response.json().get("access_token")
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_info_json = user_info.json()
    print(user_info_json)
    request.session["user"] = user_info_json
    return RedirectResponse(url="/")


@router.get("/token")
async def get_token(token: str = Depends(oauth2_scheme)):
    return jwt.decode(token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])
