import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import settings
from app.models.caller import CallerProfile
from app.models.questions import QuestionSet
from app.services import audio_store, claude_client, voice
from app.services.deps import call_store, caller_db as _db
from app.services.personalization import build_first_message, build_system_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

_question_set = QuestionSet.from_yaml(
    Path(__file__).parent.parent.parent / "data" / "questions.yaml"
)

_ERROR_TWIML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<Response>"
    "<Say>Sorry, we're experiencing a technical issue. Please try again shortly.</Say>"
    "</Response>"
)
_HANGUP_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'


def _validate_twilio(request: Request, form: dict):
    if not settings.validate_twilio_signature:
        return
    from twilio.request_validator import RequestValidator
    validator = RequestValidator(settings.twilio_auth_token)
    sig = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), form, sig):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


def _gather_twiml(audio_uuid: str) -> str:
    audio_url = f"{settings.server_url}/audio/{audio_uuid}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Gather input="speech" action="/handle-speech" method="POST"'
        ' speechTimeout="auto" timeout="10">'
        f"<Play>{audio_url}</Play>"
        "</Gather>"
        "<Redirect method=\"POST\">/handle-speech</Redirect>"
        "</Response>"
    )


@router.post("/incoming-call")
async def incoming_call(request: Request):
    form = dict(await request.form())
    _validate_twilio(request, form)

    from_number = form.get("From", "")
    call_sid = form.get("CallSid", "")
    logger.info(f"[{call_sid}] Incoming call from {from_number}")

    caller = _db.lookup(from_number) or CallerProfile(phone_number=from_number)
    first_message = build_first_message(caller)
    system_prompt = build_system_prompt(caller, _question_set)

    try:
        audio = await voice.text_to_speech(first_message)
        uid = audio_store.store(audio)
        call_store.start(call_sid, from_number, caller.display_name(), system_prompt, first_message)
        _db.increment_call_count(from_number)
        return Response(content=_gather_twiml(uid), media_type="text/xml")
    except Exception as exc:
        logger.error(f"[{call_sid}] Error on incoming call: {type(exc).__name__}: {exc}")
        return Response(content=_ERROR_TWIML, media_type="text/xml")


@router.post("/handle-speech")
async def handle_speech(request: Request):
    form = dict(await request.form())

    call_sid = form.get("CallSid", "")
    speech = (form.get("SpeechResult") or "").strip()
    logger.info(f"[{call_sid}] Speech: {speech!r}")

    state = call_store.get(call_sid)
    if state is None:
        return Response(content=_HANGUP_TWIML, media_type="text/xml")

    if not speech:
        speech = "[silence]"

    call_store.add_user(call_sid, speech)

    try:
        reply = await claude_client.get_response(state.system_prompt, state.messages)
        call_store.add_assistant(call_sid, reply)
        audio = await voice.text_to_speech(reply)
        uid = audio_store.store(audio)
        return Response(content=_gather_twiml(uid), media_type="text/xml")
    except Exception as exc:
        logger.error(f"[{call_sid}] Error on handle-speech: {type(exc).__name__}: {exc}")
        return Response(content=_ERROR_TWIML, media_type="text/xml")


@router.post("/call-status")
async def call_status(request: Request):
    """Twilio status callback — called when call ends."""
    form = dict(await request.form())
    call_sid = form.get("CallSid", "")
    status = form.get("CallStatus", "")
    logger.info(f"[{call_sid}] Call status: {status}")
    if status in ("completed", "busy", "failed", "no-answer", "canceled"):
        call_store.end(call_sid)
    return Response(content="", status_code=204)


@router.get("/audio/{uid}")
async def serve_audio(uid: str):
    audio = audio_store.get(uid)
    if audio is None:
        raise HTTPException(status_code=404, detail="Audio not found")
    return Response(content=audio, media_type="audio/mpeg")
