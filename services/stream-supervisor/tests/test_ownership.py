from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import pytest
from furbomek_stream_supervisor import shutdown as shutdown_module
from furbomek_stream_supervisor.models import RuntimePaths, RuntimeSettings, WorkerDefinition
from furbomek_stream_supervisor.ownership import record_owners
from furbomek_stream_supervisor.processes import cleanup_processes, spawn_process
from furbomek_stream_supervisor.runner import run_session
from furbomek_stream_supervisor.session import Session
from furbomek_stream_supervisor.shutdown import shutdown_session
from furbomek_stream_supervisor.support import Dependencies, SessionError, SystemClock, WorkerState
from tests.helpers import always_configure, never_bot, no_workers

if TYPE_CHECKING:
    from furbomek_stream_supervisor.processes import Clock, ManagedProcess, Sleep


def paths_for(directory: Path) -> RuntimePaths:
    return RuntimePaths.from_environment(
        directory,
        {
            "FURBOMEK_MEDIA_ROOT": str(directory / "media"),
            "FURBOMEK_KINECT_DIR": str(directory / "frames"),
            "FURBOMEK_ACTIVITY_SPOOL": str(directory / "spool/events.jsonl"),
        },
    )


def test_residual_group_blocks_next_session_until_confirmed_gone(tmp_path: Path) -> None:
    paths = paths_for(tmp_path)
    paths.media_root.mkdir()
    child = spawn_process(
        WorkerDefinition("old", (sys.executable, "-c", "import time; time.sleep(30)"), "old.log"),
        {},
        tmp_path,
    )
    record_owners(paths.media_root / "host-session.owners.json", {"old": child})
    deps = Dependencies(no_workers, always_configure, never_bot, SystemClock())
    try:
        with pytest.raises(SessionError, match="previous media workers"):
            _ = run_session(RuntimeSettings(readiness_timeout_s=1), paths, {}, deps)
        assert not paths.health.exists()
    finally:
        assert anyio.run(cleanup_processes, {"old": child}, SystemClock(), anyio.sleep)
    assert run_session(RuntimeSettings(readiness_timeout_s=1), paths, {}, deps) == 1
    assert paths.health.exists()


def test_ambiguous_spawn_is_not_automatically_cleared(tmp_path: Path) -> None:
    paths = paths_for(tmp_path)
    paths.media_root.mkdir()
    record_owners(paths.media_root / "host-session.owners.json", {}, pending_spawn=True)
    with pytest.raises(SessionError, match="operator reconciliation"):
        _ = run_session(
            RuntimeSettings(readiness_timeout_s=1),
            paths,
            {},
            Dependencies(no_workers, always_configure, never_bot, SystemClock()),
        )


def test_failed_terminal_cleanup_persists_exclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = paths_for(tmp_path)
    paths.media_root.mkdir()
    definition = WorkerDefinition(
        "old", (sys.executable, "-c", "import time; time.sleep(30)"), "old.log"
    )
    child = spawn_process(definition, {}, tmp_path)
    deps = Dependencies(no_workers, always_configure, never_bot, SystemClock())
    session = Session(RuntimeSettings(), paths, {}, deps)
    session.success = True
    session.children["old"] = child
    session.states["old"] = WorkerState(definition, child=child)

    async def refused(
        _children: Mapping[str, ManagedProcess],
        _clock: Clock,
        _sleep: Sleep,
    ) -> bool:
        return False

    monkeypatch.setattr(shutdown_module, "cleanup_processes", refused)
    try:
        anyio.run(shutdown_session, session)
        assert session.success is False
        assert session.children["old"] is child
        with pytest.raises(SessionError, match="previous media workers"):
            _ = run_session(RuntimeSettings(readiness_timeout_s=1), paths, {}, deps)
    finally:
        assert anyio.run(cleanup_processes, {"old": child}, SystemClock(), anyio.sleep)
