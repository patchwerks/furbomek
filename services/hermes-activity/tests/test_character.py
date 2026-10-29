from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import cast

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from activity_models import ActivityEvent
from character_state import MAX_RETIRED, CharacterInput, CharacterPhase, CharacterState, apply_character, expire
from hermes_feed import SpoolEvent, parse_complete_line
from persistence import load_checkpoint
from runtime import ActivityBroker, RunConfig

NOW = 1_700_000_000_000
SESSION = "fixture-session"


class FixedClock:
    def now_ms(self) -> int:
        return NOW

    def sleep(self, seconds: float) -> None:
        del seconds


def incoming(
    seq: int,
    phase: CharacterPhase = "thinking",
    *,
    utterance: str | None = None,
    cancel_of: str | None = None,
    now: int = NOW,
    ttl: int = 1_000,
    session: str = SESSION,
) -> CharacterInput:
    return CharacterInput(
        schema_version="furbomek.character-input.v1",
        session=session,
        seq=seq,
        observed_ms=now,
        ttl_ms=ttl,
        phase=phase,
        utterance=utterance,
        cancel_of=cancel_of,
    )


def row(event: CharacterInput) -> bytes:
    return (
        SpoolEvent(
            kind="character",
            ts_ms=NOW,
            session=SESSION,
            action="presentation",
            detail="",
            character=event,
        ).model_dump_json()
        + "\n"
    ).encode()


def append(spool: Path, event: CharacterInput) -> None:
    with spool.open("ab") as stream:
        stream.write(row(event))


def source(tmp_path: Path) -> Path:
    directory = tmp_path / "spool"
    directory.mkdir(mode=0o700)
    spool = directory / "events.jsonl"
    spool.touch(mode=0o600)
    return spool


def broker_for(tmp_path: Path, spool: Path, session: str | None = SESSION) -> ActivityBroker:
    return ActivityBroker(
        RunConfig(spool, tmp_path / "profile", tmp_path / "output", character_session=session), FixedClock()
    )


def published(tmp_path: Path) -> ActivityEvent:
    return ActivityEvent.model_validate_json((tmp_path / "output/activity.json").read_bytes())


def test_real_spool_broker_publisher_supports_all_states_without_public_ids(tmp_path: Path) -> None:
    spool = source(tmp_path)
    broker = broker_for(tmp_path, spool)
    fixtures = [
        incoming(0, "idle"),
        incoming(1),
        incoming(2, "speaking", utterance="private-utterance"),
        incoming(3, "interrupted", cancel_of="private-utterance"),
        incoming(4, "error"),
    ]
    previous_seq = -1
    for event in fixtures:
        append(spool, event)
        broker.step(NOW + event.seq * 10)
        actual = published(tmp_path)
        assert actual.payload.status == event.phase.upper()
        assert actual.seq > previous_seq  # Updated before the one-second heartbeat.
        assert actual.payload.screen.state == "offline"
        assert "private-utterance" not in actual.model_dump_json()
        assert SESSION not in actual.model_dump_json()
        previous_seq = actual.seq
    broker.reader.close()


def test_disabled_mode_preserves_legacy_projection(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    broker = broker_for(tmp_path, spool, session=None)
    broker.step(NOW)
    assert published(tmp_path).payload.status == "IDLE"
    assert published(tmp_path).payload.title == "Awaiting activity"
    assert broker.snapshot.broker.character is None
    broker.reader.close()


@pytest.mark.parametrize("mode", [0o644, 0o660, 0o666])
def test_nonprivate_file_cannot_publish_character(tmp_path: Path, mode: int) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    spool.chmod(mode)
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    assert published(tmp_path).payload.status != "SPEAKING"
    assert broker.snapshot.broker.character is not None
    assert broker.snapshot.broker.character.seq == -1
    broker.reader.close()


@pytest.mark.parametrize("boundary", ["directory", "symlink", "wrong-owner"])
def test_invalid_local_authority_is_denied(tmp_path: Path, boundary: str, monkeypatch: pytest.MonkeyPatch) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    broker = broker_for(tmp_path, spool)
    if boundary == "directory":
        spool.parent.chmod(0o755)
    elif boundary == "symlink":
        target = spool.with_name("target")
        spool.rename(target)
        spool.symlink_to(target)
    else:
        uid = os.getuid()
        monkeypatch.setattr("cursor.os.getuid", lambda: uid + 1)
        with pytest.raises(ValueError, match="current-UID"):
            broker.step(NOW)
        assert not (tmp_path / "output/activity.json").exists()
        denied = broker.reader.poll()
        assert denied.events == ()
        assert denied.uncertain
        broker.reader.close()
        return
    broker.step(NOW)
    assert published(tmp_path).payload.status != "SPEAKING"
    broker.reader.close()


@pytest.mark.parametrize(
    "event",
    [incoming(1), incoming(0), incoming(3, session="wrong"), incoming(3, now=NOW + 1), incoming(3, now=NOW - 1000)],
)
def test_order_session_and_freshness_reject_without_mutation(event: CharacterInput) -> None:
    state = apply_character(CharacterState(session=SESSION), incoming(1, "speaking", utterance="a"), NOW)
    assert apply_character(state, event, NOW) == state


def test_cancel_is_idempotent_and_late_completion_cannot_revive() -> None:
    state = apply_character(CharacterState(session=SESSION), incoming(0, "speaking", utterance="a"), NOW)
    cancel = incoming(1, "interrupted", cancel_of="a")
    state = apply_character(state, cancel, NOW)
    assert state.phase == "interrupted"
    assert state.utterance is None
    assert apply_character(state, cancel, NOW) == state
    assert apply_character(state, incoming(2, "speaking", utterance="a"), NOW) == state


def test_cancellation_does_not_stop_replacement_and_cannot_be_forgotten() -> None:
    state = apply_character(CharacterState(session=SESSION), incoming(0, "speaking", utterance="b"), NOW)
    state = apply_character(state, incoming(1, "interrupted", cancel_of="a"), NOW)
    assert state.phase == "speaking"
    assert state.utterance == "b"
    assert "a" in state.retired
    assert apply_character(state, incoming(2, "speaking", utterance="a"), NOW) == state


def test_expiry_clears_speech_and_bounds_published_ttl(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a", ttl=200))
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    assert published(tmp_path).ttl_ms == 200
    broker.step(NOW + 200)
    assert published(tmp_path).payload.status == "IDLE"
    append(spool, incoming(1, "speaking", utterance="a", now=NOW + 201))
    broker.step(NOW + 201)
    assert published(tmp_path).payload.status == "IDLE"
    broker.reader.close()


def test_restart_snapshot_keeps_cancellation_and_publication_sequence(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    append(spool, incoming(1, "interrupted", cancel_of="a"))
    broker.step(NOW + 1)
    before = published(tmp_path)
    broker.reader.close()
    restarted = broker_for(tmp_path, spool)
    append(spool, incoming(2, "speaking", utterance="a"))
    restarted.step(NOW + 2)
    after = published(tmp_path)
    assert after.seq > before.seq
    assert after.payload.status == "INTERRUPTED"
    assert restarted.snapshot.broker.character is not None
    assert restarted.snapshot.broker.character.seq == 1
    restarted.reader.close()


def test_missing_checkpoint_fails_closed_even_if_spool_is_replayed(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    broker.reader.close()
    (tmp_path / "output/activity.state.json").unlink()
    restarted = broker_for(tmp_path, spool)
    restarted.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    restarted.reader.close()


def test_malformed_input_clears_active_speech_without_revival(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    with spool.open("ab") as stream:
        stream.write(b"not-json\n")
    broker.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    append(spool, incoming(1, "speaking", utterance="a"))
    broker.step(NOW + 2)
    assert published(tmp_path).payload.status == "ERROR"
    broker.reader.close()


def test_retirement_capacity_fails_closed_instead_of_evicting_old_cancel() -> None:
    state = CharacterState(session=SESSION)
    for seq in range(MAX_RETIRED + 2):
        state = apply_character(state, incoming(seq, "speaking", utterance=f"u{seq}"), NOW)
    assert state.exhausted
    assert state.phase == "error"
    assert len(state.retired) == MAX_RETIRED
    assert apply_character(state, incoming(999, "speaking", utterance="u0"), NOW) == state


@pytest.mark.parametrize(
    "change",
    [
        {"seq": True},
        {"seq": 1.5},
        {"ttl_ms": 30001},
        {"ttl_ms": 0},
        {"phase": "unknown"},
        {"utterance": "bad/path"},
        {"command": "shell"},
    ],
)
def test_strict_input_rejects_malformed_or_extra_fields(change: dict[str, object]) -> None:
    raw = incoming(0).model_dump()
    raw.update(change)
    with pytest.raises(ValidationError):
        CharacterInput.model_validate_json(json.dumps(raw))


def test_missing_nested_character_payload_is_malformed() -> None:
    raw = SpoolEvent(kind="character", ts_ms=NOW, session=SESSION, action="test", detail="")
    assert parse_complete_line((raw.model_dump_json() + "\n").encode()) is None


def test_clock_reversal_retires_current_utterance() -> None:
    state = apply_character(CharacterState(session=SESSION), incoming(0, "speaking", utterance="a"), NOW)
    expired = expire(state, NOW - 1)
    assert expired.phase == "idle"
    assert "a" in expired.retired


def test_disable_and_reenable_preserves_private_cancellation_checkpoint(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    append(spool, incoming(1, "interrupted", cancel_of="a"))
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    disabled = broker_for(tmp_path, spool, session=None)
    disabled.step(NOW + 1)
    assert published(tmp_path).payload.title == "Awaiting activity"
    disabled.reader.close()
    resumed = broker_for(tmp_path, spool)
    append(spool, incoming(2, "speaking", utterance="a"))
    resumed.step(NOW + 2)
    assert published(tmp_path).payload.status == "INTERRUPTED"
    resumed.reader.close()


def test_session_identity_cannot_be_replaced_in_existing_output(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0))
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    with pytest.raises(ValueError, match="fresh private output directory"):
        broker_for(tmp_path, spool, session="different-session")


def test_cancellation_arriving_while_projection_disabled_is_kept(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "speaking", utterance="a"))
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    disabled = broker_for(tmp_path, spool, session=None)
    append(spool, incoming(1, "interrupted", cancel_of="a"))
    disabled.step(NOW + 1)
    disabled.reader.close()
    resumed = broker_for(tmp_path, spool)
    append(spool, incoming(2, "speaking", utterance="a"))
    resumed.step(NOW + 2)
    assert published(tmp_path).payload.status == "INTERRUPTED"
    resumed.reader.close()


def test_uncertain_batch_with_cancel_cannot_optimistically_recover(tmp_path: Path) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0))
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    with spool.open("ab") as stream:
        stream.write(b"not-json\n" + row(incoming(1, "interrupted", cancel_of="a")))
    first.step(NOW + 1)
    append(spool, incoming(2, "speaking", utterance="a"))
    first.step(NOW + 2)
    assert published(tmp_path).payload.status == "ERROR"
    assert first.snapshot.broker.character is not None
    assert first.snapshot.broker.character.exhausted
    first.reader.close()


def test_expired_cancel_tombstone_rejects_delayed_longer_lived_speech() -> None:
    state = apply_character(
        CharacterState(session=SESSION), incoming(2, "interrupted", cancel_of="a", ttl=100), NOW + 200
    )
    assert state.phase == "idle"  # Expired visual is never replayed.
    assert state.seq == 2
    assert "a" in state.retired
    assert apply_character(state, incoming(1, "speaking", utterance="a", ttl=1000), NOW + 200) == state
    assert apply_character(state, incoming(3, "speaking", utterance="a", ttl=1000), NOW + 200) == state


def test_late_cancellation_retires_active_speech_without_replaying_old_visual() -> None:
    state = apply_character(CharacterState(session=SESSION), incoming(4, "speaking", utterance="a"), NOW)
    cancelled = apply_character(state, incoming(2, "interrupted", cancel_of="a", ttl=100), NOW + 200)
    assert cancelled.phase == "idle"
    assert cancelled.seq == 4
    assert "a" in cancelled.retired


def test_characterless_historical_checkpoint_cannot_erase_cancellation_history(tmp_path: Path) -> None:
    spool = source(tmp_path)
    initial = broker_for(tmp_path, spool, session=None)
    initial.step(NOW)
    initial.reader.close()
    checkpoint_path = tmp_path / "output/activity.state.json"
    raw = cast("dict[str, object]", json.loads(checkpoint_path.read_text()))
    raw["version"] = 1
    cast("dict[str, object]", raw["broker"]).pop("character")
    checkpoint_path.write_text(json.dumps(raw))
    append(spool, incoming(0, "speaking", utterance="a"))
    enabled = broker_for(tmp_path, spool)
    enabled.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    enabled.reader.close()


@pytest.mark.parametrize(
    "boundary", ["directory-mode", "checkpoint-mode", "checkpoint-symlink", "directory-symlink", "owner"]
)
def test_insecure_character_checkpoint_authority_is_rejected(
    tmp_path: Path, boundary: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    spool = source(tmp_path)
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    output = tmp_path / "output"
    checkpoint = output / "activity.state.json"
    if boundary == "directory-mode":
        output.chmod(0o777)
    elif boundary == "checkpoint-mode":
        checkpoint.chmod(0o666)
    elif boundary == "checkpoint-symlink":
        target = checkpoint.with_name("target")
        checkpoint.rename(target)
        checkpoint.symlink_to(target)
    elif boundary == "directory-symlink":
        target = tmp_path / "target"
        output.rename(target)
        output.symlink_to(target, target_is_directory=True)
    else:
        uid = os.getuid()
        monkeypatch.setattr("runtime.os.getuid", lambda: uid + 1)
    with pytest.raises(ValueError, match="current-UID"):
        broker_for(tmp_path, spool)


def test_checkpoint_is_owner_only(tmp_path: Path) -> None:
    spool = source(tmp_path)
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    assert (tmp_path / "output/activity.state.json").stat().st_mode & 0o777 == 0o600
    broker.reader.close()


@pytest.mark.parametrize(
    "field", ["session", "seq", "observed_ms", "expires_ms", "phase", "utterance", "retired", "exhausted"]
)
def test_incomplete_persisted_character_fields_fail_closed(tmp_path: Path, field: str) -> None:
    spool = source(tmp_path)
    append(spool, incoming(0, "interrupted", cancel_of="a"))
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    checkpoint_path = tmp_path / "output/activity.state.json"
    raw = cast("dict[str, object]", json.loads(checkpoint_path.read_text()))
    broker_data = cast("dict[str, object]", raw["broker"])
    cast("dict[str, object]", broker_data["character"]).pop(field)
    checkpoint_path.write_text(json.dumps(raw))
    append(spool, incoming(1, "speaking", utterance="a"))
    restored = broker_for(tmp_path, spool)
    restored.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    assert restored.snapshot.broker.character is not None
    assert restored.snapshot.broker.character.exhausted
    restored.reader.close()


@pytest.mark.parametrize("boundary", ["directory", "checkpoint", "symlink"])
def test_disabled_mode_rejects_insecure_bound_checkpoint(tmp_path: Path, boundary: str) -> None:
    spool = source(tmp_path)
    first = broker_for(tmp_path, spool)
    first.step(NOW)
    first.reader.close()
    output = tmp_path / "output"
    checkpoint = output / "activity.state.json"
    if boundary == "directory":
        output.chmod(0o755)
    elif boundary == "checkpoint":
        checkpoint.chmod(0o644)
    else:
        target = checkpoint.with_name("target")
        checkpoint.rename(target)
        checkpoint.symlink_to(target)
    with pytest.raises(ValueError, match="current-UID"):
        broker_for(tmp_path, spool, session=None)


def test_private_state_guard_is_rechecked_before_consuming_more_input(tmp_path: Path) -> None:
    spool = source(tmp_path)
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    (tmp_path / "output").chmod(0o777)
    append(spool, incoming(0, "speaking", utterance="a"))
    with pytest.raises(ValueError, match="current-UID"):
        broker.step(NOW + 1)
    assert broker.snapshot.broker.character is not None
    assert broker.snapshot.broker.character.seq == -1
    broker.reader.close()


@pytest.mark.parametrize("checkpoint", ["legacy", "malformed"])
def test_missing_publication_does_not_hide_characterless_history(tmp_path: Path, checkpoint: str) -> None:
    spool = source(tmp_path)
    first = broker_for(tmp_path, spool, session=None)
    first.step(NOW)
    first.reader.close()
    (tmp_path / "output/activity.json").unlink()
    path = tmp_path / "output/activity.state.json"
    if checkpoint == "malformed":
        path.write_text("{")
    append(spool, incoming(0, "speaking", utterance="a"))
    enabled = broker_for(tmp_path, spool)
    enabled.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    enabled.reader.close()


def test_terminal_error_survives_consumer_poll_interval(tmp_path: Path) -> None:
    spool = source(tmp_path)
    broker = broker_for(tmp_path, spool)
    broker.step(NOW)
    with spool.open("ab") as stream:
        stream.write(b"malformed\n")
    broker.step(NOW + 1)
    assert published(tmp_path).payload.status == "ERROR"
    assert published(tmp_path).ttl_ms == 5000
    broker.reader.close()


def test_checkpoint_symlink_is_rejected_before_json_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}")
    link = tmp_path / "checkpoint.json"
    link.symlink_to(target)

    def forbidden(_data: object) -> None:
        pytest.fail("symlink content was read before checkpoint authority validation")

    monkeypatch.setattr("persistence.Checkpoint.model_validate_json", forbidden)
    assert load_checkpoint(link) is None


def test_default_legacy_mode_preserves_readable_output_directory(tmp_path: Path) -> None:
    spool = source(tmp_path)
    output = tmp_path / "output"
    output.mkdir(mode=0o755)
    legacy = broker_for(tmp_path, spool, session=None)
    legacy.step(NOW)
    assert published(tmp_path).payload.title == "Awaiting activity"
    assert output.stat().st_mode & 0o777 == 0o755
    legacy.reader.close()
    restarted = broker_for(tmp_path, spool, session=None)
    restarted.step(NOW + 1)
    assert published(tmp_path).payload.status == "IDLE"
    restarted.reader.close()
