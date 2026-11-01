from __future__ import annotations

import sys
import os
from dataclasses import replace
from typing import override
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))

from broker import (
    BrokerState,
    apply_event,
    idle_state,
)
from activity_models import ActivityEvent, ScreenState
from cursor import MAX_POLL_BYTES, CursorSnapshot, IncrementalSpoolReader
from furbomek_stream import observer
from hermes_feed import SpoolCategory, SpoolEvent, SpoolKind, SpoolPhase
from privacy import HoldKey, PrivacyState, apply_privacy_event
from publisher import publish
from runtime import ActivityBroker, RunConfig
from cli import app
from persistence import load_checkpoint
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


# Synthetic offline evidence stops at activity.json, without live Hermes or pixels.
SESSION = "offline-source-session-canary"
CALL = "offline-source-call-canary"
CANARIES = (
    "synthetic-secret-text-canary",
    "synthetic-result-canary",
    "synthetic-credential-canary",
    "/private/synthetic/path-canary",
)


class FixedClock:
    def __init__(self) -> None:
        self.milliseconds: int = NOW

    def now_ms(self) -> int:
        return self.milliseconds

    def sleep(self, seconds: float) -> None:
        del seconds
        message = "offline step tests must not sleep"
        raise AssertionError(message)


def _offline_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: FixedClock) -> RunConfig:
    tmp_path.chmod(0o700)
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("FURBOMEK_ACTIVITY_SPOOL", str(spool))
    monkeypatch.setattr("furbomek_stream.observer.time.time", lambda: clock.now_ms() / 1000)
    return RunConfig(spool, tmp_path / "profile", tmp_path / "output", once=True)


def _assert_redacted(raw: bytes, *, public: bool) -> None:
    for canary in CANARIES:
        assert canary.encode() not in raw
    for field in (b'"args"', b'"arguments"', b'"result"', b'"results"'):
        assert field not in raw
    if public:
        assert SESSION.encode() not in raw
        assert CALL.encode() not in raw


def _public_step(broker: ActivityBroker, now_ms: int, previous_seq: int = -1) -> ActivityEvent:
    broker.step(now_ms)
    raw = (broker.config.out_dir / "activity.json").read_bytes()
    _assert_redacted(raw, public=True)
    document = ActivityEvent.model_validate_json(raw)
    assert document.schema_version == "furbomek.character.v1"
    assert document.kind == "agent.activity"
    assert document.source == "hermes-adapter"
    assert document.audience == document.sensitivity == "public"
    assert document.ttl_ms == 5000
    assert document.seq > previous_seq
    assert document.payload.screen.state == "offline"
    assert not list(broker.config.out_dir.glob("hermes-screen-*.jpg"))
    return document


def _start_sensitive_tool() -> None:
    assert (
        observer.on_pre_tool_call(
            tool_name="browser_type",
            args={"text": CANARIES[0], "credential": CANARIES[2], "path": CANARIES[3]},
            session_id=SESSION,
            tool_call_id=CALL,
        )
        is None
    )


def _assert_tool_document(document: ActivityEvent, status: str, age_s: int) -> None:
    assert document.payload.status == "ACTING"
    assert document.payload.tool == "BROWSER"
    assert len(document.payload.timeline) == 1
    row = document.payload.timeline[0]
    assert (row.category, row.action, row.detail) == ("BROWSER", "typing", "text hidden")
    assert row.status == status
    assert row.age_s == age_s


def _assert_lifecycle_spool(config: RunConfig, status: str) -> None:
    _assert_redacted(config.spool.read_bytes(), public=False)
    assert config.spool.stat().st_mode & 0o777 == 0o600
    assert config.spool.parent.stat().st_mode & 0o777 == 0o700
    reader = IncrementalSpoolReader(config.spool, CursorSnapshot(None, 0))
    try:
        result = reader.poll()
        assert result.readable
        assert not result.gap
        assert not result.uncertain
        rows = result.events
        assert [row.kind for row in rows] == ["session_start", "thinking", "tool", "tool", "turn_done", "session_end"]
        assert [row.ts_ms for row in rows] == [NOW + index * 1000 for index in range(6)]
        assert all(row.session == SESSION for row in rows)
        assert [row.call for row in rows] == ["", "", CALL, CALL, "", ""]
        assert [row.duration_ms for row in rows] == [0, 0, 0, 37, 0, 0]
        assert [row.phase for row in rows] == ["ok", "ok", "running", status, "ok", "ok"]
        assert all(row.shutter for row in rows[2:4])
        assert reader.poll().events == ()
    finally:
        reader.close()


def _assert_restart(config: RunConfig, clock: FixedClock, cursor: CursorSnapshot, last: ActivityEvent) -> None:
    restarted = ActivityBroker(config, clock)
    try:
        assert restarted.snapshot.cursor == cursor
        assert restarted.snapshot.publication_seq == last.seq
        restored = _public_step(restarted, NOW + 11_000, last.seq)
        assert restarted.snapshot.cursor == cursor
        assert restarted.reader.poll().events == ()
        assert restored.payload.status == "IDLE"
        assert len(restored.payload.timeline) == 1
        assert restored.payload.timeline[0].status == last.payload.timeline[0].status
        assert restored.payload.timeline[0].age_s == 8
        assert restarted.snapshot.privacy.latched
        assert not restarted.snapshot.privacy.holds
    finally:
        restarted.reader.close()


@pytest.mark.parametrize("status", ["ok", "error"])
def test_offline_observer_lifecycle_reaches_public_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    clock = FixedClock()
    config = _offline_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        assert observer.on_session_start(session_id=SESSION) is None
        document = _public_step(broker, NOW + 2000)
        assert document.payload.status == "THINKING"
        clock.milliseconds += 1000
        assert observer.on_pre_llm_call(session_id=SESSION) is None
        document = _public_step(broker, NOW + 3000, document.seq)
        assert document.payload.status == "THINKING"
        clock.milliseconds += 1000
        _start_sensitive_tool()
        document = _public_step(broker, NOW + 4000, document.seq)
        _assert_tool_document(document, "running", 2)
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
        clock.milliseconds += 1000
        assert (
            observer.on_post_tool_call(
                tool_name="browser_type",
                args={"text": CANARIES[0], "credential": CANARIES[2], "path": CANARIES[3]},
                result=CANARIES[1],
                session_id=SESSION,
                tool_call_id=CALL,
                status=status,
                duration_ms=37,
            )
            is None
        )
        document = _public_step(broker, NOW + 5000, document.seq)
        _assert_tool_document(document, status, 2)
        assert broker.snapshot.privacy.latched
        assert not broker.snapshot.privacy.holds
        clock.milliseconds += 1000
        assert observer.on_post_llm_call(session_id=SESSION) is None
        document = _public_step(broker, NOW + 6000, document.seq)
        assert document.payload.status == "ACTING"
        clock.milliseconds += 1000
        assert observer.on_session_end(session_id=SESSION) is None
        document = _public_step(broker, NOW + 7000, document.seq)
        assert document.payload.status == "IDLE"
        assert document.payload.timeline[0].age_s == 4
        cursor = broker.snapshot.cursor
        assert cursor.offset == config.spool.stat().st_size
        _assert_lifecycle_spool(config, status)
    finally:
        broker.reader.close()
    _assert_restart(config, clock, cursor, document)


def test_offline_missing_completion_keeps_sensitive_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _offline_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        _start_sensitive_tool()
        document = _public_step(broker, NOW + 2000)
        _assert_tool_document(document, "running", 2)
        assert broker.snapshot.privacy.latched
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
        later = _public_step(broker, NOW + 91_000, document.seq)
        assert later.payload.status == "IDLE"
        assert len(later.payload.timeline) == 1
        assert later.payload.timeline[0].status == "running"
        assert later.payload.timeline[0].age_s == 91
        assert broker.snapshot.privacy.latched
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
        _assert_redacted(config.spool.read_bytes(), public=False)
    finally:
        broker.reader.close()


@pytest.mark.parametrize("invalid_line", [b"not-json\n", b'{"observer_failure":true}\n'])
def test_synthetic_offline_invalid_observation_preserves_latch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid_line: bytes
) -> None:
    clock = FixedClock()
    config = _offline_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        _start_sensitive_tool()
        document = _public_step(broker, NOW + 2000)
        with config.spool.open("ab") as spool:
            spool.write(invalid_line)
        reader = IncrementalSpoolReader(config.spool, broker.snapshot.cursor)
        try:
            observation = reader.poll()
            assert observation.readable
            assert observation.uncertain
            assert observation.events == ()
        finally:
            reader.close()
        document = _public_step(broker, NOW + 3000, document.seq)
        _assert_tool_document(document, "running", 3)
        assert broker.snapshot.privacy.uncertain
        assert broker.snapshot.privacy.latched
        later = _public_step(broker, NOW + 91_000, document.seq)
        assert later.payload.status == "IDLE"
        assert later.payload.timeline[0].status == "running"
        assert broker.snapshot.privacy.uncertain
        assert broker.snapshot.privacy.latched
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
    finally:
        broker.reader.close()


def _bound_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: FixedClock) -> RunConfig:
    config = _offline_config(tmp_path.resolve(), monkeypatch, clock)
    config.spool.touch(mode=0o600)
    return replace(config, once=False, hermes_session=SESSION)


def _append_bound(config: RunConfig, row: SpoolEvent) -> None:
    with config.spool.open("ab") as stream:
        stream.write(row.model_dump_json().encode() + b"\n")


@pytest.mark.parametrize(
    ("phase", "status", "title"),
    [
        ("ok", "IDLE", "Session ended"),
        ("error", "ERROR", "Session failed"),
        ("interrupted", "INTERRUPTED", "Session interrupted"),
    ],
)
def test_bound_end_is_generic_durable_and_retains_privacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, status: str, title: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        document = _bound_public_step(broker, NOW)
        _start_sensitive_tool()
        document = _bound_public_step(broker, NOW + 1, document.seq)
        assert document.payload.status == "ACTING"
        observer.on_session_end(session_id="foreign", failed=True)
        broker.step(NOW + 2)
        assert broker.snapshot.broker.phase == "acting"
        observer.on_session_end(
            session_id=SESSION, failed=phase == "error", interrupted=phase == "interrupted", error=CANARIES[0]
        )
        document = _bound_public_step(broker, NOW + 3, document.seq)
        assert document.payload.status == status
        assert document.payload.title == title
        assert document.payload.timeline == ()
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
    finally:
        broker.reader.close()
    restarted = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        observer.on_pre_llm_call(session_id=SESSION)
        observer.on_post_tool_call(session_id=SESSION, tool_call_id=CALL, status="ok")
        document = _bound_public_step(restarted, NOW + 4)
        assert document.payload.title == title
        assert document.payload.status == status
        assert restarted.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
        _assert_redacted(config.spool.read_bytes(), public=False)
    finally:
        restarted.reader.close()


@pytest.mark.parametrize("kind", ["thinking", "approval", "tool"])
def test_bound_producer_expiry_and_fresh_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        if kind == "thinking":
            observer.on_pre_llm_call(session_id=SESSION)
        elif kind == "approval":
            observer.on_pre_approval(session_key=SESSION)
        else:
            _start_sensitive_tool()
        document = _bound_public_step(broker, NOW)
        assert document.payload.status in {"THINKING", "ACTING", "AWAITING APPROVAL"}
        document = _bound_public_step(broker, NOW + 89_999, document.seq)
        assert document.payload.status != "UNKNOWN"
        document = _bound_public_step(broker, NOW + 90_000, document.seq)
        assert document.payload.status == "UNKNOWN"
        assert document.payload.title == "Activity unavailable"
        assert document.payload.timeline == ()
        if kind == "tool":
            assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
        clock.milliseconds = NOW + 90_001
        observer.on_pre_llm_call(session_id=SESSION)
        document = _bound_public_step(broker, clock.milliseconds, document.seq)
        assert document.payload.status == "THINKING"
        observer.on_post_llm_call(session_id=SESSION)
        document = _bound_public_step(broker, clock.milliseconds + 1, document.seq)
        assert document.payload.status == "IDLE"
    finally:
        broker.reader.close()


@pytest.mark.parametrize("failure", ["missing", "malformed", "marker", "truncate", "mode", "replace", "clock"])
def test_bound_observation_failure_cannot_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        _start_sensitive_tool()
        document = _bound_public_step(broker, NOW + 1)
        _damage_bound_source(config, failure)
        failure_time = NOW if failure == "clock" else NOW + 2
        document = _bound_public_step(broker, failure_time, document.seq)
        assert document.payload.status == "UNKNOWN"
        assert document.payload.timeline == ()
        assert broker.snapshot.broker.hermes is not None
        assert broker.snapshot.broker.hermes.failed
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
    finally:
        broker.reader.close()
    config.spool.touch(mode=0o600)
    config.spool.chmod(0o600)
    if failure in {"missing", "replace"}:
        with pytest.raises(ValueError, match="identity"):
            ActivityBroker(config, clock)
        return
    restarted = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        observer.on_session_end(session_id=SESSION)
        document = _bound_public_step(restarted, NOW + 3)
        assert document.payload.status == "UNKNOWN"
        assert restarted.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
    finally:
        restarted.reader.close()


def _damage_bound_source(config: RunConfig, failure: str) -> None:
    if failure == "missing":
        config.spool.unlink()
    elif failure == "malformed":
        with config.spool.open("ab") as stream:
            stream.write(b"invalid\n")
    elif failure == "marker":
        config.spool.with_suffix(".failure").touch()
    elif failure == "truncate":
        config.spool.write_bytes(b"")
    elif failure == "mode":
        config.spool.chmod(0o644)
    elif failure == "replace":
        replacement = config.spool.with_suffix(".replacement")
        replacement.touch(mode=0o600)
        replacement.replace(config.spool)


@pytest.mark.parametrize("unsafe", ["symlink", "fifo", "mode", "parent", "history", "alias"])
def test_bound_activation_rejects_unsafe_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: str) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    if unsafe == "symlink":
        other = config.spool.with_suffix(".other")
        config.spool.rename(other)
        config.spool.symlink_to(other)
    elif unsafe == "fifo":
        config.spool.unlink()
        os.mkfifo(config.spool, 0o600)
    elif unsafe == "mode":
        config.spool.chmod(0o644)
    elif unsafe == "parent":
        config.spool.parent.chmod(0o755)
    elif unsafe == "history":
        observer.on_session_start(session_id=SESSION)
    else:
        config = replace(config, spool=config.spool.parent / ".." / config.spool.parent.name / config.spool.name)
    with pytest.raises(ValueError, match=r"Hermes|private"):
        ActivityBroker(config, clock)


@pytest.mark.parametrize("change", ["omitted", "session", "spool", "character"])
def test_bound_checkpoint_rejects_rebinding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    broker.reader.close()
    if change == "omitted":
        config = replace(config, hermes_session=None)
    elif change == "session":
        config = replace(config, hermes_session="other")
    elif change == "spool":
        config = replace(config, spool=config.spool.with_suffix(".other"))
    else:
        config = replace(config, character_session=SESSION)
    with pytest.raises(ValueError, match=r"Hermes|private"):
        ActivityBroker(config, clock)


@pytest.mark.parametrize("damage", ["missing", "invalid", "old-version", "incomplete"])
def test_bound_checkpoint_cannot_reconstruct_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    broker.step(NOW)
    broker.reader.close()
    checkpoint = config.out_dir / "activity.state.json"
    raw = checkpoint.read_text()
    if damage == "missing":
        checkpoint.unlink()
    elif damage == "invalid":
        checkpoint.write_text("invalid")
    elif damage == "old-version":
        checkpoint.write_text(raw.replace('"version":3', '"version":2'))
    else:
        checkpoint.write_text(raw.replace('"ended":false,', ""))
    with pytest.raises(ValueError, match=r"Hermes|private"):
        ActivityBroker(config, clock)


def test_bound_timestamp_admission_and_delayed_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        base = event("session_start").model_copy(update={"session": SESSION})
        for timestamp in (0, NOW + 1, NOW - 90_000):
            _append_bound(config, base.model_copy(update={"ts_ms": timestamp}))
        broker.step(NOW)
        assert broker.snapshot.broker.hermes is not None
        assert not broker.snapshot.broker.hermes.started
        observer.on_session_start(session_id=SESSION)
        observer.on_pre_llm_call(session_id=SESSION)
        document = _bound_public_step(broker, NOW + 1)
        assert document.payload.status == "THINKING"
        _append_bound(config, base.model_copy(update={"kind": "tool", "phase": "running", "ts_ms": NOW - 1}))
        broker.step(NOW + 2)
        assert broker.snapshot.broker.phase == "thinking"
        _append_bound(config, base.model_copy(update={"kind": "session_end", "ts_ms": NOW - 90_001}))
        document = _bound_public_step(broker, NOW + 3)
        assert document.payload.title == "Session ended"
        assert broker.snapshot.broker.hermes.observed_ms == NOW
    finally:
        broker.reader.close()


@pytest.mark.parametrize("status", ["ok", "error"])
def test_bound_tool_completion_is_idle_with_actual_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        _start_sensitive_tool()
        document = _bound_public_step(broker, NOW)
        observer.on_post_tool_call(
            tool_name="browser_type",
            args={"text": CANARIES[0]},
            result=CANARIES[1],
            session_id=SESSION,
            tool_call_id=CALL,
            status=status,
        )
        document = _bound_public_step(broker, NOW + 1, document.seq)
        assert document.payload.status == "IDLE"
        assert document.payload.timeline[0].status == status
        assert broker.snapshot.broker.hermes is not None
        assert not broker.snapshot.broker.hermes.failed
        assert not broker.snapshot.privacy.holds
        observer.on_pre_llm_call(session_id=SESSION)
        document = _bound_public_step(broker, NOW + 2, document.seq)
        assert document.payload.status == "THINKING"
    finally:
        broker.reader.close()


def test_bound_foreign_completion_cannot_release_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        observer.on_pre_tool_call(tool_name="browser_type", session_id="foreign", tool_call_id=CALL)
        broker.step(NOW)
        assert broker.snapshot.privacy.holds == frozenset({HoldKey("foreign", CALL)})
        observer.on_post_tool_call(tool_name="browser_type", session_id="foreign", tool_call_id=CALL, status="ok")
        broker.step(NOW + 1)
        assert broker.snapshot.privacy.holds == frozenset({HoldKey("foreign", CALL)})
        assert broker.snapshot.broker.phase == "thinking"
    finally:
        broker.reader.close()


@pytest.mark.parametrize("damage", ["marker-only", "missing-marker", "stripped", "corrupt", "omitted"])
def test_bound_identity_marker_prevents_lost_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    broker.reader.close()
    marker = config.out_dir / "activity.hermes.binding.json"
    checkpoint = config.out_dir / "activity.state.json"
    assert marker.stat().st_mode & 0o777 == 0o600
    if damage == "marker-only":
        checkpoint.unlink()
    elif damage == "missing-marker":
        marker.unlink()
    elif damage == "stripped":
        raw = checkpoint.read_text()
        start = raw.index(',"hermes":')
        end = raw.index('},"privacy":', start)
        checkpoint.write_text(raw[:start] + raw[end:])
    elif damage == "corrupt":
        checkpoint.write_text("invalid")
    if damage != "missing-marker":
        config = replace(config, hermes_session=None)
    with pytest.raises(ValueError, match=r"Hermes|private"):
        ActivityBroker(config, clock)


def test_bound_quiet_polls_keep_heartbeat_cadence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        document = _bound_public_step(broker, NOW)
        output = config.out_dir / "activity.json"
        original = output.read_bytes()
        for delta in (120, 999):
            broker.step(NOW + delta)
            assert output.read_bytes() == original
            assert broker.snapshot.publication_seq == document.seq
        document = _bound_public_step(broker, NOW + 1000, document.seq)
        clock.milliseconds = NOW + 1100
        observer.on_pre_llm_call(session_id=SESSION)
        document = _bound_public_step(broker, clock.milliseconds, document.seq)
        assert document.payload.status == "THINKING"
        clock.milliseconds += 120
        observer.on_pre_approval(session_key=SESSION)
        document = _bound_public_step(broker, clock.milliseconds, document.seq)
        assert document.payload.status == "AWAITING APPROVAL"
    finally:
        broker.reader.close()


def test_bound_cli_once_in_process(tmp_path: Path) -> None:
    directory = tmp_path.resolve()
    directory.chmod(0o700)
    spool = directory / "events.jsonl"
    spool.touch(mode=0o600)
    output = directory / "output"
    result = CliRunner().invoke(
        app, [str(spool), str(directory / "profile"), str(output), "--once", "--hermes-session", SESSION]
    )
    assert result.exit_code == 0, result.output
    document = ActivityEvent.model_validate_json((output / "activity.json").read_bytes())
    assert document.payload.screen.state == "offline"
    checkpoint = load_checkpoint(output / "activity.state.json")
    assert checkpoint is not None
    assert checkpoint.broker.hermes is not None
    assert checkpoint.broker.hermes.session == SESSION
    assert (output / "activity.hermes.binding.json").is_file()


@pytest.mark.parametrize(
    "flags", [["--hermes-session", "bad/id"], ["--hermes-session", SESSION, "--character-session", SESSION]]
)
def test_bound_cli_rejects_invalid_selection(tmp_path: Path, flags: list[str]) -> None:
    output = tmp_path / "output"
    result = CliRunner().invoke(
        app, [str(tmp_path / "spool"), str(tmp_path / "profile"), str(output), "--once", *flags]
    )
    assert result.exit_code == 2
    assert not output.exists()


def test_bound_terminal_checkpoint_precedes_failed_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        _bound_public_step(broker, NOW)
        observer.on_session_end(session_id=SESSION, interrupted=True)

        def fail_publish(_state: BrokerState, _now_ms: int, _screen: ScreenState, _out_dir: Path) -> None:
            message = "injected publication failure"
            raise OSError(message)

        with monkeypatch.context() as patch:
            patch.setattr("runtime.publish", fail_publish)
            with pytest.raises(OSError, match="injected publication failure"):
                broker.step(NOW + 1)
        checkpoint = load_checkpoint(config.out_dir / "activity.state.json")
        assert checkpoint is not None
        assert checkpoint.broker.hermes is not None
        assert checkpoint.broker.hermes.ended
        assert checkpoint.broker.phase == "interrupted"
    finally:
        broker.reader.close()
    restarted = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        observer.on_pre_llm_call(session_id=SESSION)
        document = _bound_public_step(restarted, NOW + 2)
        assert document.payload.status == "INTERRUPTED"
        assert document.payload.title == "Session interrupted"
    finally:
        restarted.reader.close()


def _bound_public_step(broker: ActivityBroker, now_ms: int, previous_seq: int = -1) -> ActivityEvent:
    broker.step(now_ms)
    raw = (broker.config.out_dir / "activity.json").read_bytes()
    _assert_redacted(raw, public=True)
    document = ActivityEvent.model_validate_json(raw)
    assert document.seq > previous_seq
    assert 0 < document.ttl_ms <= 5000
    assert document.payload.screen.state == "offline"
    assert not list(broker.config.out_dir.glob("hermes-screen-*.jpg"))
    return document


@pytest.mark.parametrize("replacement_kind", ["regular", "fifo"])
def test_bound_rotation_during_poll_never_reads_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement_kind: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        _bound_public_step(broker, NOW)
        original_inode = broker.snapshot.cursor.inode
        broker.reader.close()
        reader = RotationRaceReader(config.spool, broker.snapshot.cursor, replacement_kind)
        broker.reader = reader
        document = _bound_public_step(broker, NOW + 1)
        assert document.payload.status == "UNKNOWN"
        assert broker.snapshot.cursor.inode == original_inode
        assert broker.snapshot.broker.hermes is not None
        assert broker.snapshot.broker.hermes.failed
        assert not broker.snapshot.broker.hermes.ended
        assert reader.closed
    finally:
        broker.reader.close()


@pytest.mark.parametrize("version", ["missing", '"3"', "3.0", "true"])
def test_bound_checkpoint_requires_explicit_strict_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    broker.reader.close()
    path = config.out_dir / "activity.state.json"
    replacement = "" if version == "missing" else f'"version":{version},'
    path.write_text(path.read_text().replace('"version":3,', replacement))
    assert load_checkpoint(path) is None
    for flag in (SESSION, None):
        with pytest.raises(ValueError, match="Hermes marker"):
            ActivityBroker(replace(config, hermes_session=flag), clock)


@pytest.mark.parametrize(
    ("kind", "phase"),
    [
        ("tool", "interrupted"),
        ("tool", "waiting"),
        ("approval", "ok"),
        ("thinking", "running"),
        ("session_start", "error"),
        ("turn_done", "resolved"),
        ("session_end", "running"),
    ],
)
def test_bound_invalid_kind_phase_fails_without_invented_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: SpoolKind, phase: SpoolPhase
) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        _start_sensitive_tool()
        _bound_public_step(broker, NOW)
        _append_bound(config, event(kind, phase=phase).model_copy(update={"session": SESSION}))
        document = _bound_public_step(broker, NOW + 1)
        assert document.payload.status == "UNKNOWN"
        assert document.payload.timeline == ()
        assert broker.snapshot.broker.hermes is not None
        assert broker.snapshot.broker.hermes.failed
        assert broker.snapshot.privacy.holds == frozenset({HoldKey(SESSION, CALL)})
    finally:
        broker.reader.close()


def test_legacy_interrupted_tool_is_rejected(tmp_path: Path) -> None:
    spool = tmp_path / "events.jsonl"
    spool.write_text(event("tool", phase="interrupted").model_dump_json() + "\n")
    reader = IncrementalSpoolReader(spool, CursorSnapshot(None, 0))
    try:
        result = reader.poll()
        assert result.events == ()
        assert result.uncertain
    finally:
        reader.close()


def test_bound_public_ttl_stops_at_producer_expiry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FixedClock()
    config = _bound_config(tmp_path, monkeypatch, clock)
    broker = ActivityBroker(config, clock)
    try:
        observer.on_session_start(session_id=SESSION)
        document = _bound_public_step(broker, NOW)
        document = _bound_public_step(broker, NOW + 89_999, document.seq)
        assert document.payload.status == "THINKING"
        assert document.ttl_ms == 1
        document = _bound_public_step(broker, NOW + 90_000, document.seq)
        assert document.payload.status == "UNKNOWN"
        assert document.ttl_ms == 5000
    finally:
        broker.reader.close()


class RotationRaceReader(IncrementalSpoolReader):
    def __init__(self, path: Path, snapshot: CursorSnapshot, replacement_kind: str) -> None:
        super().__init__(path, snapshot, require_private=True)
        self.replacement_kind: str = replacement_kind

    @override
    def _path_rotated(self) -> bool:
        _displace_bound_path(self.path, self.replacement_kind)
        return super()._path_rotated()

    @property
    def closed(self) -> bool:
        return self._fd is None


class DrainRaceReader(IncrementalSpoolReader):
    def __init__(self, path: Path, replacement_kind: str) -> None:
        super().__init__(path, CursorSnapshot(None, 0), require_private=True)
        self.replacement_kind: str = replacement_kind
        self.had_backlog: bool = False

    @override
    def _drain_current(self, events: list[SpoolEvent]) -> None:
        super()._drain_current(events)
        self.had_backlog = self._read_offset < self.path.stat().st_size
        _displace_bound_path(self.path, self.replacement_kind)

    @property
    def closed(self) -> bool:
        return self._fd is None


def _displace_bound_path(path: Path, replacement_kind: str) -> None:
    if replacement_kind == "mode":
        path.chmod(0o644)
        return
    path.rename(path.with_suffix(".old"))
    if replacement_kind == "fifo":
        os.mkfifo(path, 0o600)
    else:
        path.touch(mode=0o600)
        path.write_text(event("session_end").model_dump_json() + "\n")


@pytest.mark.parametrize("replacement_kind", ["regular", "fifo", "mode"])
def test_bound_rechecks_authority_after_drain_with_old_backlog(tmp_path: Path, replacement_kind: str) -> None:
    directory = tmp_path.resolve()
    directory.chmod(0o700)
    spool = directory / "events.jsonl"
    spool.touch(mode=0o600)
    line = event("thinking").model_dump_json().encode() + b"\n"
    spool.write_bytes(line * (MAX_POLL_BYTES // len(line) + 20))
    original_inode = spool.stat().st_ino
    reader = DrainRaceReader(spool, replacement_kind)
    try:
        result = reader.poll()
        assert reader.had_backlog
        assert result.events == ()
        assert not result.readable
        assert result.gap
        assert result.uncertain
        assert result.cursor.inode == original_inode
        assert reader.closed
    finally:
        reader.close()
