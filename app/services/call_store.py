import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CallState:
    call_sid: str
    from_number: str
    caller_name: str
    start_time: float
    system_prompt: str
    messages: list = field(default_factory=list)   # Claude API messages (user/assistant)
    transcript: list = field(default_factory=list)  # full log including opening greeting


class CallStore:
    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._active: dict[str, CallState] = {}
        data = self._load_raw()
        self._completed: list[dict] = data.get("completed", [])
        # Recover any calls that were active when the process last died
        for record in data.get("active", {}).values():
            record["end_time"] = record.get("end_time") or time.time()
            record["duration"] = int(record["end_time"] - record["start_time"])
            record["status"] = "recovered"
            self._completed.insert(0, record)
        if data.get("active"):
            self._write()

    # ------------------------------------------------------------------

    def _load_raw(self) -> dict:
        if self._log_path.exists():
            try:
                return json.loads(self._log_path.read_text())
            except Exception:
                pass
        return {"completed": [], "active": {}}

    def _write(self):
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        active_snapshot = {
            sid: {
                "call_sid": s.call_sid,
                "from_number": s.from_number,
                "caller_name": s.caller_name,
                "start_time": s.start_time,
                "message_count": len(s.transcript),
                "transcript": s.transcript,
            }
            for sid, s in self._active.items()
        }
        payload = {
            "completed": self._completed[:500],
            "active": active_snapshot,
        }
        self._log_path.write_text(json.dumps(payload, indent=2))

    # ------------------------------------------------------------------

    def start(
        self,
        call_sid: str,
        from_number: str,
        caller_name: str,
        system_prompt: str,
        first_message: str,
    ) -> CallState:
        state = CallState(
            call_sid=call_sid,
            from_number=from_number,
            caller_name=caller_name,
            start_time=time.time(),
            system_prompt=system_prompt,
            messages=[],
            transcript=[{"role": "assistant", "content": first_message}],
        )
        self._active[call_sid] = state
        self._write()
        return state

    def get(self, call_sid: str) -> Optional[CallState]:
        return self._active.get(call_sid)

    def add_user(self, call_sid: str, content: str):
        state = self._active.get(call_sid)
        if state:
            state.messages.append({"role": "user", "content": content})
            state.transcript.append({"role": "user", "content": content})

    def add_assistant(self, call_sid: str, content: str):
        state = self._active.get(call_sid)
        if state:
            state.messages.append({"role": "assistant", "content": content})
            state.transcript.append({"role": "assistant", "content": content})
            self._write()  # persist after every full exchange

    def end(self, call_sid: str):
        state = self._active.pop(call_sid, None)
        if state:
            end_time = time.time()
            record = {
                "call_sid": state.call_sid,
                "from_number": state.from_number,
                "caller_name": state.caller_name,
                "start_time": state.start_time,
                "end_time": end_time,
                "duration": int(end_time - state.start_time),
                "message_count": len(state.transcript),
                "transcript": state.transcript,
                "status": "completed",
            }
            self._completed.insert(0, record)
            self._write()

    def recent(self, limit: int = 50) -> list:
        return self._completed[:limit]

    def find(self, call_sid: str) -> Optional[dict]:
        for r in self._completed:
            if r["call_sid"] == call_sid:
                return r
        return None
