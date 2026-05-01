from dataclasses import dataclass
from typing import Optional


@dataclass
class CallerProfile:
    phone_number: str
    name: str = "there"
    nickname: Optional[str] = None
    notes: Optional[str] = None
    vibe_prompt: Optional[str] = None
    call_count: int = 0
    is_known: bool = False

    def display_name(self) -> str:
        return self.nickname or self.name
