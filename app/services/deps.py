from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.caller_db import CallerDatabase
from app.services.call_store import CallStore

_APP_DIR = Path(__file__).parent.parent          # .../app/
_REPO_DIR = _APP_DIR.parent                      # repo root

# Use a persistent data directory when configured (e.g. Render disk at /data),
# otherwise fall back to the repo's data/ folder for local development.
_DATA_DIR = Path(settings.data_dir) if settings.data_dir else _REPO_DIR / "data"

caller_db = CallerDatabase(_DATA_DIR / "callers.json")
call_store = CallStore(_DATA_DIR / "calls.json")
templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))
