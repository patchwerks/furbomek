from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from broker import (
    BrokerState,
    apply_event,
    idle_state,
)
from activity_models import ActivityEvent, ScreenState
from hermes_feed import SpoolCategory, SpoolEvent, SpoolKind, SpoolPhase
from privacy import PrivacyState, apply_privacy_event
from publisher import publish
from screen import desktop_health, offline_screen, read_desktop_env

NOW = 1_700_000_000_000


def event(
    kind: SpoolKind,
    *,
    phase: SpoolPhase = "ok",
    category: SpoolCategory = "AGENT",
    action: str = "using a tool",
    detail: str = "",
    shutter: bool = False,
    duration_ms: int = 0,
    call: str = "",
    privacy_release: bool = False,
) -> SpoolEvent:
    return SpoolEvent(
        kind=kind,
        ts_ms=NOW,
        session="s",
        phase=phase,
        category=category,
        action=action,
        detail=detail,
        shutter=shutter,
        duration_ms=duration_ms,
        call=call,
        privacy_release=privacy_release,
    )


def test_tool_running_then_done_builds_timeline() -> None:
    state = BrokerState(0, "idle", "Idle", "", "AGENT", (), shutter=False, session_open=True, last_event_ms=NOW)
    state = apply_event(
        state, event("tool", phase="running", category="BROWSER", action="opening", detail="example.com"), NOW
    )
    assert state.phase == "acting"
    assert state.tool == "BROWSER"
    assert state.timeline[0].status == "running"
    done = apply_event(
        state, event("tool", phase="ok", category="BROWSER", action="opening", detail="example.com"), NOW + 900
    )
    assert done.timeline[0].status == "ok"
    assert done.timeline[0].age_s == 0


def test_vault_event_latch_does_not_expire_without_release() -> None:
    state = PrivacyState.initial(checkpoint_valid=True)
    state = apply_privacy_event(
        state,
        event(
            "tool",
            phase="running",
            category="BROWSER",
            action="using password vault",
            detail="screen hidden",
            shutter=True,
            call="vault",
        ),
    )
    assert state.latched
    assert state.holds


def test_screen_offline_when_desktop_down() -> None:
    assert offline_screen(0, 0).state == "offline"


def test_long_tool_run_demotes_to_idle() -> None:
    state = BrokerState(0, "acting", "t", "", "TERMINAL", (), shutter=False, session_open=True, last_event_ms=NOW)
    assert idle_state(state, NOW + 91_000).phase == "idle"
    assert idle_state(state, NOW + 10_000).phase == "acting"


def test_publish_writes_validated_v2_contract(tmp_path: Path) -> None:
    state = BrokerState(
        3,
        "acting",
        "Browser · opening",
        "example.com",
        "BROWSER",
        (),
        shutter=False,
        session_open=True,
        last_event_ms=NOW,
    )
    screen = ScreenState(state="live", filename="hermes-screen-1.jpg", seq=7, width=960, height=540, captured_at_ms=NOW)
    publish(state, NOW, screen, tmp_path)
    document = ActivityEvent.model_validate_json((tmp_path / "activity.json").read_text(encoding="utf-8"))
    assert document.schema_version == "furbomek.character.v1"
    assert document.source == "hermes-adapter"
    assert document.payload.screen.seq == 7
    assert document.payload.timeline == ()
    assert document.payload.title == state.title
    assert document.payload.summary == state.summary
    assert document.payload.status == "ACTING"
    assert document.payload.tool == state.tool


def test_desktop_env_requires_bot_display(tmp_path: Path) -> None:
    home = tmp_path / "bot-desktop"
    home.mkdir()
    (home / "env").write_text("DISPLAY=:1\nXAUTHORITY=/tmp/x\n", encoding="utf-8")
    home.chmod(0o700)
    (home / "env").chmod(0o600)
    (home / "launcher.pid").write_text("999999999", encoding="utf-8")
    assert read_desktop_env(tmp_path)["DISPLAY"] == ":1"
    assert not desktop_health(tmp_path).alive
