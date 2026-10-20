from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path

import anyio
import pytest
from furbomek_stream_supervisor import session as session_module
from furbomek_stream_supervisor.models import (
    RuntimePaths,
    RuntimeSettings,
    WorkerDefinition,
    WorkerStatus,
)
from furbomek_stream_supervisor.processes import (
    Clock,
    ManagedProcess,
    Sleep,
    cleanup_processes,
    spawn_process,
)
from furbomek_stream_supervisor.session import Session
from furbomek_stream_supervisor.support import Dependencies, SystemClock
from supervisor import configure_obs, configure_obs_interruptible
from tests.helpers import always_configure, never_bot


def test_configure_ignoring_term_is_bounded_and_killed(tmp_path: Path) -> None:
    node = tmp_path / "node"
    _ = node.write_text("#!/bin/sh\ntrap '' TERM\nsleep 30\n", encoding="utf-8")
    _ = node.chmod(0o755)
    paths = RuntimePaths.from_environment(
        tmp_path, {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media")}
    )
    started = time.monotonic()
    assert configure_obs(paths, {"PATH": str(tmp_path)}, 0.1) is False
    assert time.monotonic() - started < 2


def test_interruptible_config_kills_owned_helper_on_stop_event(tmp_path: Path) -> None:
    node = tmp_path / "node"
    _ = node.write_text("#!/bin/sh\ntrap '' TERM\nsleep 30\n", encoding="utf-8")
    _ = node.chmod(0o755)
    paths = RuntimePaths.from_environment(
        tmp_path, {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media")}
    )
    stop_event = threading.Event()
    threading.Timer(0.1, stop_event.set).start()
    started = time.monotonic()
    result = configure_obs_interruptible(paths, {"PATH": str(tmp_path)}, 30.0, stop_event)
    assert result is False
    assert time.monotonic() - started < 2.0


def test_child_group_cleanup_kills_descendant_after_leader_exit(tmp_path: Path) -> None:
    pid_file = tmp_path / "descendant.pid"
    child = spawn_process(
        WorkerDefinition(
            "fixture",
            (
                sys.executable,
                "-c",
                f"""import subprocess
p=subprocess.Popen(['sleep','30'])
open({str(pid_file)!r},'w').write(str(p.pid))""",
            ),
            "fixture.log",
        ),
        {},
        tmp_path,
    )
    _ = child.process.wait(timeout=1)
    assert anyio.run(cleanup_processes, {"fixture": child}, SystemClock(), anyio.sleep)
    assert pid_file.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text(encoding="utf-8")), 0)


def test_failed_cleanup_retains_owner_instead_of_restarting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = RuntimePaths.from_environment(tmp_path, {"FURBOMEK_MEDIA_ROOT": str(tmp_path)})
    definition = WorkerDefinition("fixture", (sys.executable, "-c", "pass"), "fixture.log")
    session = Session(
        RuntimeSettings(),
        paths,
        {},
        Dependencies(
            lambda _settings, _paths: (definition,), always_configure, never_bot, SystemClock()
        ),
    )

    async def refused(
        _children: Mapping[str, ManagedProcess],
        _clock: Clock,
        _sleep: Sleep,
        grace_s: float = 5.0,
    ) -> bool:
        _ = grace_s
        return False

    monkeypatch.setattr(session_module, "cleanup_processes", refused)
    assert anyio.run(session.run) == 1
    assert session.stop_reason is not None
    assert "refusing another owner" in session.stop_reason
    assert session.states["fixture"].status is WorkerStatus.FAILED
