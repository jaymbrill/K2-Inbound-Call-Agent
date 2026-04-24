import logging

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.routes.twilio import router as twilio_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(title="K2 Inbound Call Agent")
app.include_router(twilio_router)


@app.get("/health")
async def health():
    return {"status": "ok", "agent_id": settings.elevenlabs_agent_id or "not configured"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
