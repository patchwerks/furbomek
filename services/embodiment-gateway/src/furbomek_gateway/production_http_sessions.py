"""Bounded, expiring local owner sessions; credentials never enter a URL."""

import secrets
import time
from dataclasses import dataclass
from threading import Lock

from pydantic import SecretStr


@dataclass(frozen=True, slots=True)
class Session:
    """CSRF and cookie expire together on a monotonic clock."""

    csrf: str
    expires: float


MIN_TOKEN = 32
MAX_TOKEN = 128
MAX_TTL = 3600
MAX_SESSIONS = 32


class Sessions:
    """Mutable bounded session table, protected across request threads."""

    def __init__(self, bootstrap: SecretStr, ttl: int = 900, limit: int = 8) -> None:
        """Require explicitly supplied entropy and bounded configuration."""
        token = bootstrap.get_secret_value()
        if (
            not MIN_TOKEN <= len(token) <= MAX_TOKEN
            or not token.isascii()
            or not all(char.isalnum() or char in "-_" for char in token)
            or not 1 <= ttl <= MAX_TTL
            or not 1 <= limit <= MAX_SESSIONS
        ):
            msg = "invalid local session configuration"
            raise ValueError(msg)
        self.bootstrap: SecretStr = bootstrap
        self.ttl: int = ttl
        self.limit: int = limit
        self._sessions: dict[str, Session] = {}
        self._lock: Lock = Lock()

    def create(self, bearer: str) -> tuple[str, Session] | None:
        """Authenticate once per bootstrap, refusing excess sessions."""
        with self._lock:
            now = time.monotonic()
            self._sessions = {
                key: value
                for key, value in self._sessions.items()
                if value.expires > now
            }
            if (
                not secrets.compare_digest(
                    bearer.encode(),
                    f"Bearer {self.bootstrap.get_secret_value()}".encode(),
                )
                or len(self._sessions) >= self.limit
            ):
                return None
            cookie = secrets.token_urlsafe(32)
            session = Session(secrets.token_urlsafe(32), now + self.ttl)
            self._sessions[cookie] = session
            return cookie, session

    def find(self, cookie: str) -> Session | None:
        """Return only an unexpired session."""
        with self._lock:
            session = self._sessions.get(cookie)
            if session is None or session.expires <= time.monotonic():
                _ = self._sessions.pop(cookie, None)
                return None
            return session
