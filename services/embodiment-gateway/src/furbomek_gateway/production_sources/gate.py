"""Bounded source admission counters; durable dispatch belongs to the sequencer."""

from collections import deque
from typing import Final

from furbomek_gateway.reaction_contracts import PrivateEvent

from .contracts import SourcePolicy, reject

MAX_SEEN: Final = 2000


class EventGate:
    """Mutable per-source dedupe/rate state retained across transport reconnect."""

    def __init__(self, policy: SourcePolicy) -> None:
        """Start bounded process-local admission state."""
        self.policy: SourcePolicy = policy
        self._seen: dict[str, int] = {}
        self._recent: deque[tuple[int, str]] = deque()
        self._last_ms: int = 0

    def admit(self, event: PrivateEvent, user: str) -> None:
        """Consume identity once, with bounded retention and source/user caps."""
        now = event.received_ms
        if now < self._last_ms:
            reject("stale")
        self._last_ms = now
        self._seen = {key: end for key, end in self._seen.items() if end >= now}
        while self._recent and self._recent[0][0] <= now - 60000:
            _ = self._recent.popleft()
        if event.stable_id in self._seen:
            reject("duplicate")
        if (
            len(self._recent) >= self.policy.rate.source_per_minute
            or sum(actor == user for _, actor in self._recent)
            >= self.policy.rate.user_per_minute
        ):
            reject("rate")
        if len(self._seen) >= MAX_SEEN:
            reject("capacity")
        self._seen[event.stable_id] = event.retain_until_ms
        self._recent.append((now, user))

    def observe(self, stable_id: str, now_ms: int) -> None:
        """Tombstone a snapshot identity so a replay cannot become a fresh cue."""
        self._seen = {key: end for key, end in self._seen.items() if end >= now_ms}
        if stable_id not in self._seen and len(self._seen) >= MAX_SEEN:
            reject("capacity")
        self._seen[stable_id] = now_ms + 60000
