from __future__ import annotations

import os
import signal
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from furbomek_stream_supervisor.models import (
    HealthDocument,
    HealthState,
    RuntimePaths,
    RuntimeSettings,
    WorkerDefinition,
)
from furbomek_stream_supervisor.runner import run_session
from furbomek_stream_supervisor.session import Session
from furbomek_stream_supervisor.support import Dependencies, SystemClock
from tests.helpers import (
    always_configure,
    command,
    fresh_artifacts,
    never_bot,
    producer_command,
)

if TYPE_CHECKING:
    import pytest
    from furbomek_stream_supervisor.processes import ManagedProcess


def test_startup_child_failure_restarts_within_readiness_deadline(tmp_path: Path) -> None:
    kinect = tmp_path / "kinect"
    kinect.mkdir()
    stable = command("import time; time.sleep(30)")
    crash_once = command(
        f"""import time
from pathlib import Path
marker=Path({str(tmp_path / "crash.marker")!r})
time.sleep(.1)
if marker.exists(): time.sleep(30)
marker.write_text('x')
raise SystemExit(1)"""
    )
    workers = (
        WorkerDefinition("capture", crash_once, "capture.log"),
        WorkerDefinition("tracker", producer_command(kinect), "tracker.log"),
        WorkerDefinition("broker", stable, "broker.log"),
        WorkerDefinition("viewer", stable, "viewer.log", presentation=True),
        WorkerDefinition("obs", stable, "obs.log", presentation=True, starts_after_configure=True),
    )
    paths = RuntimePaths.from_environment(
        tmp_path,
        {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"), "FURBOMEK_KINECT_DIR": str(kinect)},
    )
    deps = Dependencies(
        lambda settings, resolved: workers, always_configure, never_bot, SystemClock()
    )
    result = run_session(RuntimeSettings(readiness_timeout_s=3), paths, {}, deps)
    assert result == 0
    health = HealthDocument.model_validate_json(paths.health.read_bytes())
    assert health.stop_reason == "viewer closed by operator"


def test_immediate_obs_exit_never_publishes_ready(tmp_path: Path) -> None:
    kinect = tmp_path / "kinect"
    kinect.mkdir()
    stable = command("import time; time.sleep(30)")
    workers = (
        WorkerDefinition("capture", producer_command(kinect), "capture.log"),
        WorkerDefinition("tracker", stable, "tracker.log"),
        WorkerDefinition("broker", stable, "broker.log"),
        WorkerDefinition("viewer", stable, "viewer.log", presentation=True),
        WorkerDefinition(
            "obs",
            command("raise SystemExit(0)"),
            "obs.log",
            presentation=True,
            starts_after_configure=True,
        ),
    )
    paths = RuntimePaths.from_environment(
        tmp_path,
        {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"), "FURBOMEK_KINECT_DIR": str(kinect)},
    )
    result = run_session(
        RuntimeSettings(readiness_timeout_s=2),
        paths,
        {},
        Dependencies(
            lambda settings, resolved: workers, always_configure, never_bot, SystemClock()
        ),
    )
    assert result == 0
    assert (
        HealthDocument.model_validate_json(paths.health.read_bytes()).stop_reason
        == "obs closed by operator"
    )


def test_stale_prelaunch_artifacts_do_not_ready(tmp_path: Path) -> None:
    paths = RuntimePaths.from_environment(
        tmp_path,
        {
            "FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"),
            "FURBOMEK_KINECT_DIR": str(tmp_path / "kinect"),
        },
    )
    paths.kinect_dir.mkdir()
    fresh_artifacts(paths.kinect_dir)
    stable = command("import time; time.sleep(30)")
    workers = (
        *tuple(
            WorkerDefinition(key, stable, f"{key}.log") for key in ("capture", "tracker", "broker")
        ),
        WorkerDefinition("viewer", stable, "viewer.log", presentation=True),
        WorkerDefinition("obs", stable, "obs.log", starts_after_configure=True),
    )
    result = run_session(
        RuntimeSettings(readiness_timeout_s=1),
        paths,
        {},
        Dependencies(
            lambda settings, resolved: workers, always_configure, never_bot, SystemClock()
        ),
    )
    assert result == 1
    assert HealthDocument.model_validate_json(paths.health.read_bytes()).state == "failed"


def test_signal_during_interruptible_config_never_starts_obs(tmp_path: Path) -> None:
    kinect = tmp_path / "kinect"
    kinect.mkdir()
    stable = command("import time; time.sleep(30)")
    workers = (
        *tuple(
            WorkerDefinition(
                key, producer_command(kinect) if key == "capture" else stable, f"{key}.log"
            )
            for key in ("capture", "tracker", "broker")
        ),
        WorkerDefinition(
            "viewer", command("import time; time.sleep(.2)"), "viewer.log", presentation=True
        ),
        WorkerDefinition("obs", stable, "obs.log", starts_after_configure=True),
    )
    stop_event_seen: list[bool] = []

    def configure(
        paths: RuntimePaths, env: Mapping[str, str], timeout_s: float, stop_event: threading.Event
    ) -> bool:
        _ = paths, env, timeout_s
        for _ in range(100):
            if stop_event.is_set():
                stop_event_seen.append(True)
                return False
            time.sleep(0.01)
        return True

    paths = RuntimePaths.from_environment(
        tmp_path,
        {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"), "FURBOMEK_KINECT_DIR": str(kinect)},
    )
    timer = threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        result = run_session(
            RuntimeSettings(readiness_timeout_s=2),
            paths,
            {},
            Dependencies(
                lambda settings, resolved: workers,
                always_configure,
                never_bot,
                SystemClock(),
                configure_with_stop=configure,
            ),
        )
    finally:
        timer.cancel()
    assert result == 0
    assert stop_event_seen == [True]


def test_false_record_finalizer_fails_health_but_cleans(tmp_path: Path) -> None:
    kinect = tmp_path / "kinect"
    kinect.mkdir()
    stable = command("import time; time.sleep(30)")
    workers = (
        *tuple(
            WorkerDefinition(
                key, producer_command(kinect) if key == "capture" else stable, f"{key}.log"
            )
            for key in ("capture", "tracker", "broker")
        ),
        WorkerDefinition(
            "viewer", command("import time; time.sleep(.2)"), "viewer.log", presentation=True
        ),
        WorkerDefinition("obs", stable, "obs.log", starts_after_configure=True),
    )
    paths = RuntimePaths.from_environment(
        tmp_path,
        {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"), "FURBOMEK_KINECT_DIR": str(kinect)},
    )

    def false_finalizer(child: ManagedProcess, env: Mapping[str, str], timeout_s: float) -> bool:
        _ = child, env, timeout_s
        return False

    result = run_session(
        RuntimeSettings(record=True, readiness_timeout_s=2),
        paths,
        {},
        Dependencies(
            lambda settings, resolved: workers,
            always_configure,
            never_bot,
            SystemClock(),
            graceful_obs_stop=false_finalizer,
        ),
    )
    health = HealthDocument.model_validate_json(paths.health.read_bytes())
    assert result == 1
    assert health.state == "failed"
    assert health.stop_reason == "OBS recording finalization failed"


def test_stopping_health_publication_failure_still_cleans_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kinect = tmp_path / "kinect"
    kinect.mkdir()
    stable = command("import time; time.sleep(30)")
    workers = (
        WorkerDefinition("capture", producer_command(kinect), "capture.log"),
        WorkerDefinition("tracker", stable, "tracker.log"),
        WorkerDefinition("broker", stable, "broker.log"),
        WorkerDefinition(
            "viewer", command("import time; time.sleep(.2)"), "viewer.log", presentation=True
        ),
        WorkerDefinition("obs", stable, "obs.log", presentation=True, starts_after_configure=True),
    )
    original_publish = Session.publish

    def failing_stopping_publish(session: Session) -> None:
        if session.state is HealthState.STOPPING:
            raise OSError("injected stopping publication failure")
        original_publish(session)

    monkeypatch.setattr(Session, "publish", failing_stopping_publish)
    paths = RuntimePaths.from_environment(
        tmp_path,
        {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"), "FURBOMEK_KINECT_DIR": str(kinect)},
    )
    result = run_session(
        RuntimeSettings(readiness_timeout_s=2),
        paths,
        {},
        Dependencies(
            lambda settings, resolved: workers, always_configure, never_bot, SystemClock()
        ),
    )
    assert result == 1
    health = HealthDocument.model_validate_json(paths.health.read_bytes())
    assert health.state == "failed"
    assert all(worker.pid is None for worker in health.workers.values())
