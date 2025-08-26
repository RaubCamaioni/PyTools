from app import ENVIRONMENT
from fastapi import Depends, APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from app.models.tools import SessionDep, User, hash_id, get_user
from app import TEMPLATES
import requests
from pydantic import ValidationError
import jwt

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.get("/login/button", response_class=HTMLResponse)
async def login_button(request: Request):
    logged = "user" in request.session

    if logged:
        try:
            user: User = User.model_validate_json(request.session.get("user"))
        except ValidationError:
            del request.session["user"]
            logged = False

    if logged:
        name = user.alias
        kwargs = {"request": request, "name": name}
        button_html = TEMPLATES.TemplateResponse("components/logout_button.html", kwargs)
    else:
        kwargs = {"request": request, "url": ENVIRONMENT.LOGIN_URL}
        button_html = TEMPLATES.TemplateResponse(
            "components/login_button.html",
            kwargs,
        )

    return button_html


@router.post("/logout/button", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    kwargs = {"request": request, "url": ENVIRONMENT.LOGIN_URL}
    button_html = TEMPLATES.TemplateResponse("components/login_button.html", kwargs)
    return button_html


@router.get("/auth/google")
async def auth_google(request: Request, code: str, session: SessionDep):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": ENVIRONMENT.GOOGLE_CLIENT_ID,
        "client_secret": ENVIRONMENT.GOOGLE_CLIENT_SECRET,
        "redirect_uri": ENVIRONMENT.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)

    if response.status_code != 200:
        raise HTTPException(status_code=403, detail="Access denied")

    payload: dict = response.json()

    access_token = payload.get("access_token")
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_info_json = user_info.json()
    id = hash_id(user_info_json["id"])
    request.session["user"] = get_user(session, id).model_dump_json()

    return RedirectResponse(url="/")


@router.get("/token")
async def get_token(token: str = Depends(oauth2_scheme)):
    return jwt.decode(token, ENVIRONMENT.GOOGLE_CLIENT_SECRET, algorithms=["HS256"])
