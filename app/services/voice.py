import httpx
from app.config import settings


async def text_to_speech(text: str) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.content
