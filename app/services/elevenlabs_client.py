"""
ElevenLabs Conversational AI client.

Primary flow  — register_call():
  POST /v1/convai/twilio/register_call with caller overrides.
  ElevenLabs returns TwiML; we pass it straight to Twilio.
  Twilio then streams audio directly to ElevenLabs infrastructure — no proxy needed.

Fallback flow — build_stream_twiml():
  We build TwiML ourselves pointing to our /media-stream WebSocket proxy.
  Use this if register_call() raises NotImplementedError.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.elevenlabs.io"
_REGISTER_CALL_PATH = "/v1/convai/twilio/register_call"


async def register_call(
    first_message: str,
    system_prompt: str,
    dynamic_variables: dict[str, str],
) -> str:
    """
    Register an inbound call with ElevenLabs.
    Returns TwiML XML string to return directly to Twilio.
    """
    payload = {
        "agent_id": settings.elevenlabs_agent_id,
        "conversation_initiation_client_data": {
            "dynamic_variables": dynamic_variables,
            "conversation_config_override": {
                "agent": {
                    "first_message": first_message,
                    "prompt": {
                        "prompt": system_prompt,
                    },
                },
            },
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE_URL}{_REGISTER_CALL_PATH}",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10.0,
        )

        if resp.status_code in (404, 405):
            raise NotImplementedError(
                f"ElevenLabs register_call endpoint returned {resp.status_code}. "
                "Switch Twilio webhook to /incoming-call/proxy instead."
            )

        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            data = resp.json()
            return data.get("twiml") or data.get("xml") or str(data)

        return resp.text


def build_stream_twiml(caller_number: str) -> str:
    """
    Fallback: TwiML that points Twilio at our local WebSocket proxy.
    The proxy connects to ElevenLabs and injects caller context mid-stream.
    """
    ws_base = (
        settings.server_url
        .replace("https://", "wss://")
        .replace("http://", "ws://")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{ws_base}/media-stream">'
        f'<Parameter name="caller_number" value="{caller_number}"/>'
        "</Stream>"
        "</Connect>"
        "</Response>"
    )
