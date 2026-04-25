from pathlib import Path

import yaml
import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.models.caller import CallerProfile
from app.services.deps import caller_db, call_store

router = APIRouter(prefix="/api")

_EL_BASE = "https://api.elevenlabs.io"
_QUESTIONS_PATH = Path(__file__).parent.parent.parent / "data" / "questions.yaml"


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@router.get("/debug")
async def debug():
    """Check API key validity and ElevenLabs connectivity."""
    key = settings.elevenlabs_api_key
    preview = (key[:8] + "…" + key[-4:]) if len(key) > 12 else "too short / missing"

    result: dict = {
        "api_key_preview": preview,
        "api_key_length": len(key),
        "anthropic_key_set": bool(settings.anthropic_api_key),
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{_EL_BASE}/v1/user",
                headers={"xi-api-key": key},
                timeout=10.0,
            )
            if resp.is_success:
                user = resp.json()
                result["elevenlabs_auth"] = "OK"
                result["account_email"] = user.get("email", "(hidden)")
            else:
                result["elevenlabs_auth"] = f"FAILED — {resp.status_code}"
                result["elevenlabs_error"] = resp.text
        except Exception as exc:
            result["elevenlabs_auth"] = f"ERROR — {exc}"

    return result


# ---------------------------------------------------------------------------
# Call history — from local call log
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_conversations(limit: int = 30):
    return {"conversations": call_store.recent(limit)}


@router.get("/conversations/{call_sid}")
async def get_conversation(call_sid: str):
    record = call_store.find(call_sid)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return record


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
