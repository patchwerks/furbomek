from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

from runtime import ActivityBroker, RunConfig
from tests.test_character import SESSION, FixedClock, append, incoming, source

ROOT = Path(__file__).resolve().parents[3]


def test_real_broker_snapshots_reach_godot_control_and_reconnect(tmp_path: Path) -> None:
    godot = os.environ.get("FURBOMEK_GODOT")
    if not godot:
        pytest.skip("FURBOMEK_GODOT is required for actual Godot consumer qualification")
    spool = source(tmp_path)
    output = tmp_path / "output"
    broker = ActivityBroker(RunConfig(spool, tmp_path / "profile", output, character_session=SESSION), FixedClock())
    now_ms = int(time.time() * 1000)
    fixtures = [
        incoming(0, "idle", now=now_ms, ttl=30000),
        incoming(1, now=now_ms, ttl=30000),
        incoming(2, "speaking", utterance="fixture-a", now=now_ms, ttl=30000),
        incoming(3, "interrupted", cancel_of="fixture-a", now=now_ms, ttl=30000),
        incoming(4, "error", now=now_ms, ttl=30000),
    ]
    for event in fixtures:
        append(spool, event)
        broker.step(now_ms)
        shutil.copyfile(output / "activity.json", output / f"case-{event.seq}.json")
    with spool.open("ab") as stream:
        stream.write(b"malformed\n")
    broker.step(now_ms + 1)
    shutil.copyfile(output / "activity.json", output / "case-5.json")
    broker.reader.close()
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(ROOT / "tools/kinect2/godot"),
            "--script",
            "res://character_fixture_runner.gd",
            "--",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHARACTER CONTROL FIXTURES PASS" in result.stdout
    assert "SCRIPT ERROR" not in result.stderr
    for line in result.stdout.splitlines():
        if line.startswith("CHARACTER CONTROL "):
            print(line)  # noqa: T201 - Fixed fixture timing evidence is intentionally included in CI logs.
