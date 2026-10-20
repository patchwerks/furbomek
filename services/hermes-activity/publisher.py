"""Atomic Godot activity publication."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from activity_models import ActivityEvent, ActivityPayload, BrokerState, ScreenState


def publish(state: BrokerState, now_ms: int, screen: ScreenState, out_dir: Path) -> None:
    """Write one validated public activity event atomically."""
    payload = ActivityPayload(
        title=state.title,
        summary=state.summary,
        status=state.phase.upper(),
        tool=state.tool,
        timeline=state.timeline,
        screen=screen,
    )
    event = ActivityEvent(seq=state.seq, observed_at=_observed_at(now_ms), payload=payload)
    pending = out_dir / "activity.next.json"
    pending.write_text(event.model_dump_json(by_alias=True), encoding="utf-8")
    pending.replace(out_dir / "activity.json")


def _observed_at(now_ms: int) -> str:
    return datetime.fromtimestamp(now_ms / 1000, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
