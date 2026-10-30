"""Pure Hermes event reduction and timeline aging."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, assert_never

from activity_models import BrokerState, TimelineEntry, event_time

if TYPE_CHECKING:
    from hermes_feed import SpoolEvent

TIMELINE_LIMIT = 6
IDLE_AFTER_MS = 90_000


def apply_event(state: BrokerState, event: SpoolEvent, now_ms: int) -> BrokerState:
    """Reduce one event using its producer timestamp for timeline ages."""
    event_ms = event_time(event, now_ms)
    match event.kind:
        case "character":
            # Only ActivityBroker's opt-in, authorized path may consume this input.
            return state
        case "session_start":
            return replace(
                state,
                phase="thinking",
                title="Session started",
                summary="Hermes is starting a new session",
                tool="AGENT",
                session_open=True,
                last_event_ms=event_ms,
                shutter=state.shutter or event.shutter,
            )
        case "thinking":
            return replace(
                state,
                phase="thinking",
                title="Thinking",
                summary="Hermes is planning its next step",
                tool="AGENT",
                last_event_ms=event_ms,
                shutter=state.shutter or event.shutter,
            )
        case "turn_done":
            return replace(
                state,
                title="Responded",
                summary="Hermes finished this step",
                tool="AGENT",
                last_event_ms=event_ms,
                shutter=state.shutter or event.shutter,
            )
        case "session_end":
            return replace(
                state,
                phase="idle",
                title="Responded",
                summary="Hermes finished this step",
                tool="AGENT",
                session_open=False,
                last_event_ms=event_ms,
                shutter=state.shutter or event.shutter,
            )
        case "approval":
            return _apply_approval(state, event, event_ms)
        case "tool":
            return replace(
                state,
                phase="acting",
                title=f"{event.category.title()} · {event.action}",
                summary=event.detail or event.action,
                tool=event.category,
                timeline=_timeline(state, event, event_ms),
                last_event_ms=event_ms,
                shutter=state.shutter or event.shutter,
            )
        case unreachable:
            assert_never(unreachable)


def _apply_approval(state: BrokerState, event: SpoolEvent, event_ms: int) -> BrokerState:
    if event.phase == "waiting":
        return replace(
            state,
            phase="awaiting approval",
            title="Awaiting approval",
            summary="Waiting for the operator to approve an action",
            tool="AGENT",
            last_event_ms=event_ms,
            shutter=state.shutter or event.shutter,
        )
    if event.phase == "resolved":
        return replace(
            state,
            title="Approval resolved",
            summary="Continuing",
            tool="AGENT",
            last_event_ms=event_ms,
            shutter=state.shutter or event.shutter,
        )
    return state


def idle_state(state: BrokerState, now_ms: int) -> BrokerState:
    """Demote stale activity without touching privacy state."""
    if state.phase != "acting" or now_ms - state.last_event_ms < IDLE_AFTER_MS:
        return state
    return replace(state, phase="idle", title="Idle", summary="No recent Hermes activity", tool="AGENT")


def refresh_timeline(state: BrokerState, now_ms: int) -> BrokerState:
    """Recompute ages from original producer timestamps."""
    timeline = tuple(
        item.model_copy(update={"age_s": min(86_400, max(0, (now_ms - item.event_ts_ms) // 1000))})
        for item in state.timeline
    )
    return replace(state, timeline=timeline)


def _timeline(state: BrokerState, event: SpoolEvent, event_ms: int) -> tuple[TimelineEntry, ...]:
    rows = [row for row in state.timeline if row.status != "running" or row.action != event.action]
    status = "running" if event.phase == "running" else "error" if event.phase == "error" else "ok"
    rows.insert(
        0,
        TimelineEntry(
            age_s=0,
            category=event.category,
            action=event.action,
            detail=event.detail,
            status=status,
            event_ts_ms=event_ms,
        ),
    )
    return tuple(rows[:TIMELINE_LIMIT])
