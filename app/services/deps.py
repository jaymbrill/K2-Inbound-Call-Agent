from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.services.caller_db import CallerDatabase
from app.services.call_store import CallStore

# Absolute paths so they resolve correctly regardless of working directory
_APP_DIR = Path(__file__).parent.parent          # .../app/
_REPO_DIR = _APP_DIR.parent                      # repo root

caller_db = CallerDatabase(_REPO_DIR / "data" / "callers.json")
call_store = CallStore(_REPO_DIR / "data" / "calls.json")
templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))
