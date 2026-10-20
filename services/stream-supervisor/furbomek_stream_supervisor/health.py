"""Typed health document construction and atomic publication."""

from __future__ import annotations

from typing import Protocol

from .models import (
    FreshnessHealth,
    HealthDocument,
    HealthState,
    RuntimePaths,
    RuntimeSettings,
    WorkerHealth,
)
from .support import RESTART_WINDOW_S, Dependencies, WorkerState


class HealthSource(Protocol):
    """Session fields required to publish health."""

    paths: RuntimePaths
    deps: Dependencies
    states: dict[str, WorkerState]
    state: HealthState
    freshness: FreshnessHealth
    stop_reason: str | None
    settings: RuntimeSettings


def publish(source: HealthSource) -> None:
    """Atomically publish one validated health document."""
    now = source.deps.clock.monotonic()
    workers: dict[str, WorkerHealth] = {}
    for key, state in source.states.items():
        while state.restart_times and now - state.restart_times[0] >= RESTART_WINDOW_S:
            _ = state.restart_times.popleft()
        child = state.child
        workers[key] = WorkerHealth(
            pid=child.pid if child else None,
            pgid=child.pgid if child else None,
            status=state.status,
            restarts_in_window=len(state.restart_times),
            last_exit=state.last_exit,
        )
    document = HealthDocument(
        state=source.state,
        ready=source.state is HealthState.READY,
        published_at_unix_ms=int(source.deps.clock.time() * 1000),
        record_requested=source.settings.record,
        stop_reason=source.stop_reason,
        freshness=source.freshness,
        workers=workers,
    )
    pending = source.paths.health.with_name("health.next.json")
    _ = pending.write_text(document.model_dump_json(), encoding="utf-8")
    _ = pending.chmod(0o600)
    _ = pending.replace(source.paths.health)
