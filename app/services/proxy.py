"""
WebSocket proxy: sits between Twilio and ElevenLabs.

Used when the ElevenLabs register_call API is unavailable.
Twilio streams audio to /media-stream; we connect to ElevenLabs' Twilio
endpoint, inject a contextual_update with caller info, then relay all
messages bidirectionally.
"""

import asyncio
import json
import logging

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.models.caller import CallerProfile
from app.services.caller_db import CallerDatabase
from app.services.personalization import build_first_message

logger = logging.getLogger(__name__)

# db is injected at call time to share the same instance as the route layer
_EL_WS_URL = "wss://api.elevenlabs.io/v1/convai/twilio"

async def handle_media_stream(websocket: WebSocket, db: CallerDatabase):
    await websocket.accept()

    el_url = f"{_EL_WS_URL}?agent_id={settings.elevenlabs_agent_id}"

    try:
        async with websockets.connect(
            el_url,
            additional_headers={"xi-api-key": settings.elevenlabs_api_key},
        ) as el_ws:

            async def twilio_to_el():
                async for raw in websocket.iter_text():
                    data = json.loads(raw)
                    event = data.get("event", "")

                    if event == "start":
                        params = data.get("start", {}).get("customParameters", {})
                        caller_number = params.get("caller_number", "")
                        call_sid = data.get("start", {}).get("callSid", "")
                        logger.info(f"[{call_sid}] Proxy stream — caller: {caller_number}")

                        caller = db.lookup(caller_number) or CallerProfile(
                            phone_number=caller_number
                        )

                        # Forward start first so ElevenLabs can initialize the session
                        await el_ws.send(raw)

                        # Inject caller context into the conversation
                        context = (
                            f"Caller name: {caller.display_name()}. "
                            f"Open with this exact greeting: {build_first_message(caller)}"
                        )
                        if caller.notes:
                            context += f" Caller context: {caller.notes}"

                        await el_ws.send(
                            json.dumps({"type": "contextual_update", "text": context})
                        )

                        db.increment_call_count(caller_number)

                    elif event == "stop":
                        await el_ws.send(raw)
                        break

                    else:
                        await el_ws.send(raw)

            async def el_to_twilio():
                async for msg in el_ws:
                    if isinstance(msg, bytes):
                        msg = msg.decode()
                    await websocket.send_text(msg)

            tasks = [
                asyncio.create_task(twilio_to_el()),
                asyncio.create_task(el_to_twilio()),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except WebSocketDisconnect:
        pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as exc:
        logger.error(f"Proxy error: {type(exc).__name__}: {exc}")
