import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket
from twilio.request_validator import RequestValidator

from app.config import settings
from app.models.caller import CallerProfile
from app.models.questions import QuestionSet
from app.services.caller_db import CallerDatabase
from app.services.elevenlabs_client import build_stream_twiml, register_call
from app.services.personalization import (
    build_dynamic_variables,
    build_first_message,
    build_system_prompt,
)
from app.services.proxy import handle_media_stream

router = APIRouter()
logger = logging.getLogger(__name__)

_db = CallerDatabase(Path("data/callers.json"))
_question_set = QuestionSet.from_yaml(Path("data/questions.yaml"))

_ERROR_TWIML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<Response>"
    "<Say>Sorry, we're experiencing a technical issue. Please try again shortly.</Say>"
    "</Response>"
)


def _validate_twilio_signature(request: Request, form: dict):
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


# ---------------------------------------------------------------------------
# Primary: ElevenLabs register_call — no proxy, Twilio streams to ElevenLabs
# ---------------------------------------------------------------------------

@router.post("/incoming-call")
async def incoming_call(request: Request):
    form = dict(await request.form())

    if settings.validate_twilio_signature:
        _validate_twilio_signature(request, form)

    from_number = form.get("From", "")
    call_sid = form.get("CallSid", "")
    logger.info(f"[{call_sid}] Incoming call from {from_number}")

    caller = _db.lookup(from_number) or CallerProfile(phone_number=from_number)

    first_message = build_first_message(caller)
    system_prompt = build_system_prompt(caller, _question_set)
    dynamic_vars = build_dynamic_variables(caller)

    try:
        twiml = await register_call(first_message, system_prompt, dynamic_vars)
        _db.increment_call_count(from_number)
        return Response(content=twiml, media_type="text/xml")

    except NotImplementedError as exc:
        logger.warning(f"[{call_sid}] {exc}")
        # Graceful fallback: redirect to proxy endpoint
        twiml = build_stream_twiml(from_number)
        return Response(content=twiml, media_type="text/xml")

    except Exception as exc:
        logger.error(f"[{call_sid}] ElevenLabs error: {type(exc).__name__}: {exc}")
        return Response(content=_ERROR_TWIML, media_type="text/xml")


# ---------------------------------------------------------------------------
# Fallback: WebSocket proxy — configure Twilio to POST here if needed
# ---------------------------------------------------------------------------

@router.post("/incoming-call/proxy")
async def incoming_call_proxy(request: Request):
    form = dict(await request.form())

    if settings.validate_twilio_signature:
        _validate_twilio_signature(request, form)

    from_number = form.get("From", "")
    call_sid = form.get("CallSid", "")
    logger.info(f"[{call_sid}] Incoming call (proxy mode) from {from_number}")

    twiml = build_stream_twiml(from_number)
    return Response(content=twiml, media_type="text/xml")


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await handle_media_stream(websocket)
