"""Atomic Godot activity publication."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from activity_models import ActivityEvent, ActivityPayload, BrokerState, ScreenState
from character_state import expire

PUBLIC_TTL_MS = 5_000


def publish(state: BrokerState, now_ms: int, screen: ScreenState, out_dir: Path) -> None:
    """Write one validated public activity event atomically."""
    character = expire(state.character, now_ms) if state.character is not None else None
    payload = ActivityPayload(
        title=state.title,
        summary=state.summary,
        status=state.phase.upper(),
        tool=state.tool,
        timeline=state.timeline,
        screen=screen,
    )
    ttl_ms = PUBLIC_TTL_MS
    if character is not None:
        payload = payload.model_copy(
            update={
                "title": character.phase.title(),
                "summary": "Character status",
                "status": character.phase.upper(),
                "tool": "AGENT",
            }
        )
        if character.phase != "idle" and not character.exhausted:
            ttl_ms = min(PUBLIC_TTL_MS, max(1, character.expires_ms - now_ms))
    event = ActivityEvent(seq=state.seq, observed_at=_observed_at(now_ms), ttl_ms=ttl_ms, payload=payload)
    pending = out_dir / "activity.next.json"
    pending.write_text(event.model_dump_json(by_alias=True), encoding="utf-8")
    pending.replace(out_dir / "activity.json")


def _observed_at(now_ms: int) -> str:
    return datetime.fromtimestamp(now_ms / 1000, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
