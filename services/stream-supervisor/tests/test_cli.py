from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from furbomek_stream_supervisor.models import (
    RuntimePaths,
    RuntimeSettings,
    ScreenPolicy,
    WorkerDefinition,
)
from furbomek_stream_supervisor.runner import run_session
from furbomek_stream_supervisor.support import Dependencies, SessionError, SystemClock
from supervisor import build_worker_definitions, load_settings, main
from tests.helpers import always_configure, never_bot


def test_worker_argv_and_recording_are_explicit(tmp_path: Path) -> None:
    paths = RuntimePaths.from_environment(tmp_path, {"FURBOMEK_MEDIA_ROOT": str(tmp_path)})
    workers = build_worker_definitions(RuntimeSettings(record=True), paths)
    by_key = {worker.key: worker for worker in workers}
    assert "--startrecording" in by_key["obs"].argv
    assert by_key["obs"].starts_after_configure
    assert by_key["broker"].argv[-2:] == ("--screen-policy", "off")
    assert "--project" in by_key["broker"].argv


def test_bot_desktop_policy_is_blocked_before_lock_or_spawn(tmp_path: Path) -> None:
    paths = RuntimePaths.from_environment(
        tmp_path, {"FURBOMEK_MEDIA_ROOT": str(tmp_path / "media")}
    )

    def forbidden_workers(
        settings: RuntimeSettings, resolved: RuntimePaths
    ) -> tuple[WorkerDefinition, ...]:
        _ = settings, resolved
        raise AssertionError("worker definitions must not be evaluated")

    with pytest.raises(SessionError, match="observer-only privacy contract"):
        _ = run_session(
            RuntimeSettings(screen_policy=ScreenPolicy.BOT_DESKTOP),
            paths,
            {},
            Dependencies(forbidden_workers, always_configure, never_bot, SystemClock()),
        )
    assert not paths.media_root.exists()


def test_cli_help_bad_settings_and_missing_settings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--help"]) == 0
    assert "--settings" in capsys.readouterr().out
    bad = tmp_path / "settings.json"
    _ = bad.write_text('{"schema_version":1,"unexpected":true}', encoding="utf-8")
    _ = bad.chmod(0o600)
    assert main(["--settings", str(bad)]) == 2
    assert load_settings(tmp_path / "missing.json").screen_policy is ScreenPolicy.OFF


def test_stream_cli_rejects_screen_policy_before_mutation(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "systemctl.log"
    stub = bin_dir / "systemctl"
    _ = stub.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$*" >>"$SYSTEMCTL_LOG"\nprintf active\n', encoding="utf-8"
    )
    _ = stub.chmod(0o755)
    script = Path(__file__).resolve().parents[3] / "tools/kinect2/stream.sh"
    env = dict(
        os.environ,
        XDG_RUNTIME_DIR=str(runtime),
        PATH=f"{bin_dir}:{os.environ['PATH']}",
        SYSTEMCTL_LOG=str(log),
    )
    _ = subprocess.run(["bash", str(script), "start", "--record"], env=env, check=True)
    settings = runtime / "furbomek-stream/settings.json"
    blocked = subprocess.run(
        ["bash", str(script), "start", "--screen-policy", "bot-desktop"], env=env, check=False
    )
    assert blocked.returncode == 2
    assert (
        RuntimeSettings.model_validate_json(settings.read_bytes()).screen_policy is ScreenPolicy.OFF
    )
