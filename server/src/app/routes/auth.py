"""Login with GitHub (OAuth web flow).

The site needs a GitHub OAuth app (Settings > Developer settings > OAuth Apps) whose
callback URL is GITHUB_REDIRECT_URI; its client id/secret come from the environment.
Without them the site still runs, with the login button disabled.
"""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError

from app import ENVIRONMENT, TEMPLATES, logger
from app.models.tools import SessionDep, User, get_user, hash_id

router = APIRouter()

# the account that uploaded the original tools, created under the old Google login
OWNER_USER_ID = 49600918
OWNER_GITHUB_LOGIN = ENVIRONMENT.OWNER_GITHUB_LOGIN
DEFAULT_ALIAS = "annonymous"  # matches the User model default
RECENT_STATES = 5  # login states kept per session (one per rendered login button)


class GitHubLoginError(Exception):
    """GitHub rejected the code or the user lookup failed."""


class GitHubOAuth:
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"

    def __init__(self, client_id: Optional[str], client_secret: Optional[str], redirect_uri: str):
        self.client_id, self.client_secret, self.redirect_uri = client_id, client_secret, redirect_uri
        self.transport: Optional[httpx.AsyncBaseTransport] = None  # tests inject a MockTransport

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def login_url(self, state: str) -> str:
        query = {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "scope": "read:user", "state": state}
        return f"{self.AUTHORIZE_URL}?{urlencode(query)}"

    async def user_for_code(self, code: str) -> dict:
        """Exchange the callback code for the GitHub user's id and login."""
        async with httpx.AsyncClient(timeout=15, transport=self.transport) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            payload = response.json() if response.status_code == 200 else {}
            token = payload.get("access_token")
            if not token:
                # GitHub reports a bad exchange with HTTP 200 and an error field
                reason = payload.get("error", f"HTTP {response.status_code}")
                raise GitHubLoginError(f"token exchange failed: {reason}: {payload.get('error_description', '')}".rstrip(": "))
            user = await client.get(
                self.USER_URL,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            if user.status_code != 200:
                raise GitHubLoginError(f"user lookup failed: {user.status_code}")
            data = user.json()
            return {"id": data["id"], "login": data["login"]}


github = GitHubOAuth(ENVIRONMENT.GITHUB_CLIENT_ID, ENVIRONMENT.GITHUB_CLIENT_SECRET, ENVIRONMENT.GITHUB_REDIRECT_URI)


def _session_user(request: Request) -> Optional[User]:
    if "user" not in request.session:
        return None
    try:
        return User.model_validate_json(request.session["user"])
    except ValidationError:
        del request.session["user"]
        return None


def session_user(request: Request) -> Optional[User]:
    """The logged-in user from the session cookie, or None."""
    return _session_user(request)


def session_alias(request: Request) -> str:
    """What the header centre shows: the logged-in alias, or 'anonymous'."""
    user = _session_user(request)
    return user.alias if user is not None else "anonymous"


def session_admin(request: Request) -> bool:
    user = _session_user(request)
    return bool(user is not None and user.admin)


TEMPLATES.env.globals["session_alias"] = session_alias
TEMPLATES.env.globals["session_admin"] = session_admin


def _login_button(request: Request) -> HTMLResponse:
    user = _session_user(request)
    if user is not None:
        return TEMPLATES.TemplateResponse(request, "components/logout_button.html", {"name": user.alias})
    url = None
    if github.configured:
        state = secrets.token_urlsafe(24)
        # every page render issues a new state; keep the last few so an older tab's login still works
        request.session["oauth_states"] = (request.session.get("oauth_states") or [])[-(RECENT_STATES - 1) :] + [state]
        url = github.login_url(state)
    return TEMPLATES.TemplateResponse(request, "components/login_button.html", {"url": url})


@router.get("/login/button", response_class=HTMLResponse)
async def login_button(request: Request):
    return _login_button(request)


@router.post("/logout/button", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    return _login_button(request)


@router.get("/auth/github")
async def auth_github(request: Request, code: str, state: str, session: SessionDep):
    expected = request.session.pop("oauth_states", None) or []
    if not any(secrets.compare_digest(candidate, state) for candidate in expected):
        raise HTTPException(status_code=403, detail="Login state mismatch, try again")

    try:
        account = await github.user_for_code(code)
    except GitHubLoginError as e:
        logger.warning(f"github login failed: {e}")
        raise HTTPException(status_code=403, detail="GitHub login failed")

    user_id = OWNER_USER_ID if account["login"] == OWNER_GITHUB_LOGIN else hash_id(f"github:{account['id']}")
    user = get_user(session, user_id)
    if user.banned:
        raise HTTPException(status_code=403, detail="This account is banned")
    if user.alias == DEFAULT_ALIAS:
        user.alias = account["login"]
        session.commit()

    request.session["user"] = user.model_dump_json()
    return RedirectResponse(url="/")


@router.get("/whoami")
async def whoami(request: Request):
    user = _session_user(request)
    if user is None:
        return JSONResponse({"detail": "not logged in"}, status_code=401)
    return JSONResponse({"id": user.id, "alias": user.alias})
