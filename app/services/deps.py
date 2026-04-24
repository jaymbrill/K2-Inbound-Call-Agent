from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.services.caller_db import CallerDatabase

# Shared singletons imported by all route modules — keeps db state consistent
caller_db = CallerDatabase(Path("data/callers.json"))
templates = Jinja2Templates(directory="app/templates")
