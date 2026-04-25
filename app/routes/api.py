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
# Voices — list available ElevenLabs voices including clones
# ---------------------------------------------------------------------------

@router.get("/voices")
async def list_voices():
    """Returns all voices in your ElevenLabs account, including cloned ones."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_EL_BASE}/v1/voices",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=10.0,
        )
        if not resp.is_success:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        voices = resp.json().get("voices", [])
        return [
            {
                "voice_id": v["voice_id"],
                "name": v["name"],
                "category": v.get("category", ""),
                "current": v["voice_id"] == settings.elevenlabs_voice_id,
            }
            for v in voices
        ]


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@router.get("/debug")
async def debug():
    """Check all external dependencies and config."""
    from app.services import voice

    el_key = settings.elevenlabs_api_key
    result: dict = {
        "elevenlabs_key_preview": (el_key[:8] + "…" + el_key[-4:]) if len(el_key) > 12 else "MISSING",
        "elevenlabs_voice_id": settings.elevenlabs_voice_id,
        "anthropic_key_set": bool(settings.anthropic_api_key),
        "server_url": settings.server_url,
        "validate_twilio_signature": settings.validate_twilio_signature,
    }

    # Test ElevenLabs auth
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{_EL_BASE}/v1/user",
                headers={"xi-api-key": el_key},
                timeout=10.0,
            )
            result["elevenlabs_auth"] = "OK" if resp.is_success else f"FAILED {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            result["elevenlabs_auth"] = f"ERROR: {exc}"

    # Test ElevenLabs TTS (short phrase)
    try:
        audio = await voice.text_to_speech("Hello.")
        result["elevenlabs_tts"] = f"OK — {len(audio)} bytes"
    except Exception as exc:
        result["elevenlabs_tts"] = f"FAILED: {exc}"

    # Test Anthropic
    if settings.anthropic_api_key:
        try:
            from app.services import claude_client
            reply = await claude_client.get_response("Say only: OK", [{"role": "user", "content": "ping"}])
            result["anthropic_claude"] = f"OK — replied: {reply[:60]}"
        except Exception as exc:
            result["anthropic_claude"] = f"FAILED: {exc}"
    else:
        result["anthropic_claude"] = "SKIPPED — ANTHROPIC_API_KEY not set"

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


@router.post("/conversations/{call_sid}/summarize")
async def summarize_conversation(call_sid: str):
    from app.services import claude_client
    record = call_store.find(call_sid)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    transcript = record.get("transcript", [])
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript to summarize")

    formatted = "\n".join(
        f"{'K2' if t['role'] == 'assistant' else 'Caller'}: {t['content']}"
        for t in transcript
    )
    summary = await claude_client.get_response(
        "You summarize phone conversations concisely. "
        "Given a transcript between K2 (AI assistant) and a caller, write 2-3 sentences covering: "
        "who called (if known), the main topics discussed, and any key information or follow-ups. "
        "Be specific. Do not use bullet points.",
        [{"role": "user", "content": f"Summarize this call:\n\n{formatted}"}],
    )
    call_store.set_summary(call_sid, summary)
    return {"summary": summary}


@router.post("/conversations/summarize-all")
async def summarize_all():
    from app.services import claude_client
    results = []
    for record in call_store.recent(200):
        if record.get("summary"):
            continue
        transcript = record.get("transcript", [])
        if not transcript:
            continue
        formatted = "\n".join(
            f"{'K2' if t['role'] == 'assistant' else 'Caller'}: {t['content']}"
            for t in transcript
        )
        try:
            summary = await claude_client.get_response(
                "You summarize phone conversations concisely. "
                "Given a transcript between K2 (AI assistant) and a caller, write 2-3 sentences covering: "
                "who called (if known), the main topics discussed, and any key information or follow-ups. "
                "Be specific. Do not use bullet points.",
                [{"role": "user", "content": f"Summarize this call:\n\n{formatted}"}],
            )
            call_store.set_summary(record["call_sid"], summary)
            results.append({"call_sid": record["call_sid"], "ok": True})
        except Exception as exc:
            results.append({"call_sid": record["call_sid"], "ok": False, "error": str(exc)})
    return {"summarized": len([r for r in results if r["ok"]]), "results": results}


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
