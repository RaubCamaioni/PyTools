from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from app.models.tools import SessionDep

router = APIRouter()


@router.get("/tools/upload", response_class=JSONResponse)
def tool_upload(requst: Request, session: SessionDep):
    pass


@router.get("/tools/delete", response_class=JSONResponse)
def tool_delete(requst: Request, session: SessionDep):
    pass
