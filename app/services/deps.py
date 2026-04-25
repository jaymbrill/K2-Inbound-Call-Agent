from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.caller_db import CallerDatabase
from app.services.call_store import CallStore

_APP_DIR = Path(__file__).parent.parent          # .../app/
_REPO_DIR = _APP_DIR.parent                      # repo root

# Use a persistent data directory when configured (e.g. Render disk at /data).
# Fall back to repo data/ if the configured path doesn't exist or isn't writable
# (e.g. disk not yet attached), so the app still starts cleanly.
def _resolve_data_dir() -> Path:
    if settings.data_dir:
        p = Path(settings.data_dir)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    fallback = _REPO_DIR / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

_DATA_DIR = _resolve_data_dir()

caller_db = CallerDatabase(_DATA_DIR / "callers.json")
call_store = CallStore(_DATA_DIR / "calls.json")
templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))
