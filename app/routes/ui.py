from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services.deps import templates

router = APIRouter(prefix="/ui")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "calls"})


@router.get("/callers", response_class=HTMLResponse)
async def callers(request: Request):
    return templates.TemplateResponse("callers.html", {"request": request, "page": "callers"})


@router.get("/questions", response_class=HTMLResponse)
async def questions(request: Request):
    return templates.TemplateResponse("questions.html", {"request": request, "page": "questions"})
