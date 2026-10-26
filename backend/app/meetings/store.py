from __future__ import annotations
import secrets, time, threading, hashlib
from dataclasses import dataclass, field
from typing import Any

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

@dataclass
class MeetingSession:
    meeting_id: str
    token_digest: str
    source: str
    title: str
    meeting_date: str
    raw_text: str = ""
    segments: list[dict[str, Any]] = field(default_factory=list)
    spec: dict[str, Any] | None = None
    state: str = "created"
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 1800)
    provider: str = "mock"
    lock: threading.Lock = field(default_factory=threading.Lock)
    bot_id: str | None = None
    meeting_url: str | None = None

class MeetingStore:
    def __init__(self):
        self._items: dict[str, MeetingSession] = {}
        self._lock = threading.RLock()

    def create(self, source: str, title: str, meeting_date: str, text: str = "") -> tuple[MeetingSession, str]:
        token = secrets.token_urlsafe(32)
        meeting_id = secrets.token_urlsafe(12).replace("-", "a").replace("_", "b")
        item = MeetingSession(meeting_id, token_hash(token), source, title, meeting_date, text)
        with self._lock:
            self._purge_expired()
            self._items[meeting_id] = item
        return item, token

    def _purge_expired(self):
        now = time.time()
        for key in [k for k,v in self._items.items() if v.expires_at < now]:
            del self._items[key]

    def get(self, meeting_id: str) -> MeetingSession | None:
        with self._lock:
            self._purge_expired()
            return self._items.get(meeting_id)

    def check_token(self, meeting_id: str, token: str) -> bool:
        item = self.get(meeting_id)
        return bool(item and secrets.compare_digest(item.token_digest, token_hash(token)))

    def extend(self, meeting_id: str, seconds: int = 1800):
        item = self.get(meeting_id)
        if item:
            item.expires_at = time.time() + seconds

    def delete(self, meeting_id: str):
        with self._lock:
            self._items.pop(meeting_id, None)

store = MeetingStore()
