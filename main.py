import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routes.twilio import router as twilio_router
from app.routes.api import router as api_router
from app.routes.ui import router as ui_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(title="K2 Inbound Call Agent")
app.include_router(twilio_router)
app.include_router(api_router)
app.include_router(ui_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
async def health():
    return {"status": "ok", "agent_id": settings.elevenlabs_agent_id or "not configured"}


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
