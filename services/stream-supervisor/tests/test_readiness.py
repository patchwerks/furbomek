from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, override

import anyio
from furbomek_stream_supervisor.models import (
    HealthState,
    RuntimePaths,
    RuntimeSettings,
    WorkerDefinition,
)
from furbomek_stream_supervisor.session import Session
from furbomek_stream_supervisor.support import Dependencies, SystemClock
from tests.helpers import command, never_bot, producer_command

if TYPE_CHECKING:
    import pytest


def test_configuration_cannot_publish_expired_producer_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class OffsetClock(SystemClock):
        offset: float = 0.0

        @override
        def time(self) -> float:
            return time.time() + self.offset

    clock = OffsetClock()
    paths = RuntimePaths.from_environment(
        tmp_path,
        {
            "FURBOMEK_MEDIA_ROOT": str(tmp_path / "media"),
            "FURBOMEK_KINECT_DIR": str(tmp_path / "frames"),
            "FURBOMEK_ACTIVITY_SPOOL": str(tmp_path / "spool/events.jsonl"),
        },
    )
    paths.media_root.mkdir()
    paths.kinect_dir.mkdir()
    workers = (
        WorkerDefinition("producer", producer_command(paths.kinect_dir), "producer.log"),
        WorkerDefinition(
            "obs", command("import time; time.sleep(30)"), "obs.log", starts_after_configure=True
        ),
    )

    def configure(paths: RuntimePaths, env: Mapping[str, str], timeout_s: float) -> bool:
        _ = paths, env, timeout_s
        clock.offset = 2.0
        return True

    seen: list[HealthState] = []
    original_publish = Session.publish

    def observe(session: Session) -> None:
        seen.append(session.state)
        original_publish(session)
        if clock.offset and session.state in (
            HealthState.STARTING,
            HealthState.READY,
            HealthState.DEGRADED,
        ):
            session.request_stop("fixture complete", success=True)

    monkeypatch.setattr(Session, "publish", observe)
    session = Session(
        RuntimeSettings(readiness_timeout_s=5),
        paths,
        {},
        Dependencies(lambda _settings, _paths: workers, configure, never_bot, clock),
    )
    assert anyio.run(session.run) == 0
    assert HealthState.READY not in seen
