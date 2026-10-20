from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest
    from furbomek_stream.projection import JsonObject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))

from activity_models import ActivityEvent
from hermes_feed import SpoolEvent
from furbomek_stream import observer

ROOT = Path(__file__).resolve().parents[1]


def test_real_cli_once_writes_godot_activity_and_durable_checkpoint(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(
        SpoolEvent(
            kind="tool",
            ts_ms=int(time.time() * 1000),
            session="session-1",
            phase="running",
            category="BROWSER",
            action="opening",
            detail="example.com",
            call="call-1",
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    profile = tmp_path / "profile"
    output = tmp_path / "output"
    command = [
        "uv",
        "run",
        "--project",
        str(ROOT),
        "--frozen",
        "python",
        "broker.py",
        str(spool),
        str(profile),
        str(output),
        "--once",
    ]
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    result: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.seq > 0
    assert event.kind == "agent.activity"
    assert event.audience == "public"
    assert event.sensitivity == "public"
    assert event.ttl_ms <= 30_000
    assert event.observed_at.endswith("Z")
    assert event.payload.status == "ACTING"
    assert event.payload.screen.state == "offline"
    assert (output / "activity.state.json").is_file()

    second = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
    assert second.returncode == 0, second.stderr
    restarted = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert restarted.seq > event.seq


def test_observer_event_reaches_real_cli_projection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    observer.on_pre_tool_call(
        tool_name="browser_navigate", args={"url": "https://example.com"}, session_id="s", tool_call_id="nav"
    )
    observer.on_post_tool_call(
        tool_name="browser_navigate",
        args={"url": "https://example.com"},
        session_id="s",
        tool_call_id="nav",
        status="ok",
    )

    output = tmp_path / "output"
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(ROOT),
            "--frozen",
            "python",
            "broker.py",
            str(spool),
            str(tmp_path / "profile"),
            str(output),
            "--once",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    event = ActivityEvent.model_validate_json((output / "activity.json").read_text(encoding="utf-8"))
    assert event.payload.title == "Browser · opening"
    assert event.payload.timeline[0].status == "ok"


def test_bot_desktop_cli_refuses_before_profile_or_capture(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(ROOT),
            "--frozen",
            "python",
            "broker.py",
            "missing-spool",
            str(tmp_path / "profile"),
            str(tmp_path / "output"),
            "--once",
            "--screen-policy",
            "bot-desktop",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "bot-desktop capture is blocked" in result.stderr
    assert "contract is qualified" in result.stderr
    assert not (tmp_path / "profile").exists()
    assert not (tmp_path / "output").exists()


def test_observer_app_canary_never_reaches_public_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    canary = "ProjectApolloSecret"
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    arguments: JsonObject = {"action": "focus_app", "app": canary}
    observer.on_pre_tool_call(tool_name="computer_use", args=arguments, session_id="s", tool_call_id="c")
    observer.on_post_tool_call(tool_name="computer_use", args=arguments, session_id="s", tool_call_id="c", status="ok")
    output = tmp_path / "output"
    result = subprocess.run(
        [sys.executable, str(ROOT / "broker.py"), str(spool), str(tmp_path / "profile"), str(output), "--once"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    public_json = (output / "activity.json").read_text(encoding="utf-8")
    assert canary not in public_json
    assert ActivityEvent.model_validate_json(public_json).payload.timeline
