"""Bounded finalization and cleanup orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

import anyio

from .models import HealthState, RuntimeSettings, WorkerStatus
from .processes import ManagedProcess, cleanup_processes
from .support import Dependencies, WorkerState


class ShutdownSource(Protocol):
    """Session fields needed during finalization."""

    state: HealthState
    success: bool
    stop_reason: str | None
    settings: RuntimeSettings
    env: Mapping[str, str]
    children: dict[str, ManagedProcess]
    states: dict[str, WorkerState]
    deps: Dependencies
    publish: Callable[[], None]


async def shutdown_session(source: ShutdownSource) -> None:
    """Finalize requested recording, then clean every owned child."""
    source.state = HealthState.STOPPING
    try:
        source.publish()
    except OSError as error:
        source.success = False
        source.stop_reason = f"stopping health publication failed: {error}"
    obs = source.children.get("obs")
    if (
        source.settings.record
        and obs is not None
        and obs.poll() is None
        and source.deps.graceful_obs_stop is not None
    ):
        finalized = await anyio.to_thread.run_sync(
            source.deps.graceful_obs_stop,
            obs,
            source.env,
            5.0,
            abandon_on_cancel=True,
        )
        if not finalized:
            source.success = False
            source.stop_reason = "OBS recording finalization failed"
    cleaned = await cleanup_processes(source.children, source.deps.clock, source.deps.sleep)
    if not cleaned:
        source.success = False
        source.stop_reason = source.stop_reason or "child cleanup did not complete"
    source.children.clear()
    for state in source.states.values():
        if not cleaned and state.child is not None and state.child.poll() is None:
            state.status = WorkerStatus.FAILED
        else:
            state.child = None
        if state.status is not WorkerStatus.FAILED:
            state.status = WorkerStatus.STOPPED
    source.state = HealthState.STOPPED if source.success else HealthState.FAILED
    try:
        source.publish()
    except OSError as error:
        source.success = False
        source.stop_reason = f"final health publication failed: {error}"
