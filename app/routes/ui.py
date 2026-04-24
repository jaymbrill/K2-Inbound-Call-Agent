from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services.deps import templates

router = APIRouter(prefix="/ui")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"page": "calls"})


@router.get("/callers", response_class=HTMLResponse)
async def callers(request: Request):
    return templates.TemplateResponse(request, "callers.html", {"page": "callers"})


@router.get("/questions", response_class=HTMLResponse)
async def questions(request: Request):
    return templates.TemplateResponse(request, "questions.html", {"page": "questions"})
