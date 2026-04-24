import yaml
import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.models.caller import CallerProfile
from app.services.deps import caller_db

router = APIRouter(prefix="/api")

_EL_BASE = "https://api.elevenlabs.io"
_QUESTIONS_PATH = __import__("pathlib").Path("data/questions.yaml")


async def _el_get(path: str, params: dict = None):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_EL_BASE}{path}",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            params=params or {},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Call history — proxied from ElevenLabs (keeps API key server-side)
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_conversations(page_size: int = 30, cursor: str = ""):
    params = {"agent_id": settings.elevenlabs_agent_id, "page_size": page_size}
    if cursor:
        params["cursor"] = cursor
    try:
        return await _el_get("/v1/convai/conversations", params)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        return await _el_get(f"/v1/convai/conversations/{conversation_id}")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))


# ---------------------------------------------------------------------------
# Callers CRUD
# ---------------------------------------------------------------------------

@router.get("/callers")
async def get_callers():
    return caller_db.all()


@router.put("/callers/{phone_number:path}")
async def upsert_caller(phone_number: str, request: Request):
    body = await request.json()
    body["phone_number"] = phone_number
    body.setdefault("call_count", 0)
    body.setdefault("is_known", True)
    try:
        profile = CallerProfile(**body)
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    caller_db.upsert(profile)
    return {"ok": True}


@router.delete("/callers/{phone_number:path}")
async def delete_caller(phone_number: str):
    if not caller_db.delete(phone_number):
        raise HTTPException(status_code=404, detail="Caller not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Questions editor
# ---------------------------------------------------------------------------

@router.get("/questions")
async def get_questions():
    with open(_QUESTIONS_PATH) as f:
        return yaml.safe_load(f) or {}


@router.put("/questions")
async def save_questions(request: Request):
    body = await request.json()
    with open(_QUESTIONS_PATH, "w") as f:
        yaml.dump(body, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return {"ok": True}
