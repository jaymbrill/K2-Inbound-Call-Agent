import json
import logging
from pathlib import Path
from typing import Optional

from app.models.caller import CallerProfile

logger = logging.getLogger(__name__)


class CallerDatabase:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            with open(self._path) as f:
                self._data = json.load(f)
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._save()

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def lookup(self, phone_number: str) -> Optional[CallerProfile]:
        raw = self._data.get(phone_number)
        if raw is None:
            return None
        return CallerProfile(**raw)

    def upsert(self, profile: CallerProfile):
        self._data[profile.phone_number] = {
            "phone_number": profile.phone_number,
            "name": profile.name,
            "nickname": profile.nickname,
            "notes": profile.notes,
            "joke": profile.joke,
            "call_count": profile.call_count,
            "is_known": profile.is_known,
        }
        self._save()

    def all(self) -> list[dict]:
        return list(self._data.values())

    def delete(self, phone_number: str) -> bool:
        if phone_number not in self._data:
            return False
        del self._data[phone_number]
        self._save()
        return True

    def increment_call_count(self, phone_number: str):
        if phone_number in self._data:
            self._data[phone_number]["call_count"] = (
                self._data[phone_number].get("call_count", 0) + 1
            )
        else:
            self._data[phone_number] = {
                "phone_number": phone_number,
                "name": "there",
                "nickname": None,
                "notes": None,
                "joke": None,
                "call_count": 1,
                "is_known": False,
            }
        self._save()
        logger.debug(f"Call count updated for {phone_number}")
