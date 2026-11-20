from pathlib import Path

import pytest
from pydantic import ValidationError

from furbomek_gateway.effect_contracts import AppliedAck
from furbomek_gateway.reaction_contracts import PrivateEvent, parse_pack

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "packages/production-contracts/fixtures/liquidation.json"
)


def test_liquidation_pack_is_bounded_media_with_optional_motion() -> None:
    pack = parse_pack(FIXTURE.read_bytes())
    assert pack.pack_id == "liquidation"
    assert len(pack.cues) == 4
    assert pack.horizon_ms == 1200


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ('"after": []', '"after": ["hud"]', "cycle"),
        ('"priority": "curated"', '"priority": "stop"', "literal_error"),
        ('"preset": "liquidation"', '"preset": "../../secret"', "literal_error"),
        ('"schema_version": 1', '"schema_version": 2', "literal_error"),
        ('"id": "graphics"', '"id": "hud"', "duplicate"),
        ('"gain_percent": 30', '"gain_percent": 101', "less_than_equal"),
        ('"duration_ms": 1000', '"duration_ms": true', "int_type"),
        (
            '"capability": "sfx.preset.v1"',
            '"capability": "sfx.preset.v2"',
            "union_tag_invalid",
        ),
        (
            '"pack_id": "liquidation"',
            '"pack_id": "liquidation", "script": "run"',
            "extra_forbidden",
        ),
        ('"id": "graphics"', '"id": "graphics", "path": "/tmp/a"', "extra_forbidden"),
        ('"after": ["hud"]', '"after": ["missing"]', "unknown dependency"),
    ],
)
def test_pack_rejects_unsafe_input(old: str, new: str, reason: str) -> None:
    raw = FIXTURE.read_text().replace(old, new)
    with pytest.raises(ValueError, match=reason):
        _ = parse_pack(raw.encode())


def test_duplicate_json_keys_rejected() -> None:
    raw = FIXTURE.read_text().replace(
        '"pack_id": "liquidation"', '"pack_id": "a", "pack_id": "liquidation"'
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _ = parse_pack(raw.encode())


def test_event_identity_and_freshness() -> None:
    event = PrivateEvent(
        source="fixture",
        scope="stream",
        stable_id="event-1",
        causation_id="root",
        origin="adapter",
        occurred_ms=1000,
        received_ms=1100,
    )
    event.require_fresh(1200)
    assert event.dedupe_key == ("fixture", "stream", "event-1")
    assert event.retain_until_ms == 61100


@pytest.mark.parametrize("now", [999, 11001])
def test_event_rejects_future_or_stale_dispatch(now: int) -> None:
    event = PrivateEvent(
        source="fixture",
        scope="stream",
        stable_id="event-1",
        causation_id="root",
        origin="adapter",
        occurred_ms=1000,
        received_ms=1100,
    )
    with pytest.raises(ValueError, match="freshness"):
        event.require_fresh(now)


def test_event_rejects_unknown_age() -> None:
    with pytest.raises(ValidationError):
        _ = PrivateEvent.model_validate_json(
            '{"source":"fixture","scope":"stream","stable_id":"e","causation_id":"r","origin":"adapter","received_ms":1100,"occurred_ms":null}'
        )


def test_applied_ack_cannot_claim_missing_revision() -> None:
    with pytest.raises(ValidationError):
        _ = AppliedAck.model_validate_json(
            '{"status":"applied","cue_id":"hud","owner":"cue","revision":null}'
        )


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ('"after": ["hud"]', '"after": ["hud", "hud"]', "duplicate dependency"),
        (
            '"capability": "graphics.pulse.v1", "preset": "liquidation", "intensity_percent": 50',  # noqa: E501 - exact fixture fragment
            '"capability": "hud.redacted.v1", "template": "neutral"',
            "concurrent resource",
        ),
        ('"condition": "motion_qualified"', '"condition": "always"', "qualification"),
        ('"ttl_ms": 1000', '"ttl_ms": 100', "TTL"),
        ('"pack_id": "liquidation"', '"pack_id": "liquidation\\n"', "string_pattern"),
    ],
)
def test_pack_rejects_graph_and_budget_errors(old: str, new: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        _ = parse_pack(FIXTURE.read_text().replace(old, new).encode())


def test_schedule_horizon_is_sum_of_dependencies() -> None:
    raw = (
        FIXTURE.read_text()
        .replace('"duration_ms": 1000', '"duration_ms": 30000')
        .replace('"ttl_ms": 1000', '"ttl_ms": 30000')
    )
    with pytest.raises(ValueError, match="horizon"):
        _ = parse_pack(raw.encode())


def test_concurrent_physical_cues_rejected_even_on_distinct_resources() -> None:
    raw = (
        FIXTURE.read_text()
        .replace(
            '"capability": "graphics.pulse.v1", "preset": "liquidation", "intensity_percent": 50',  # noqa: E501 - exact fixture fragment
            '"capability": "face.reserved.v1", "preset": "reserved"',
        )
        .replace('"condition": "always"', '"condition": "motion_qualified"')
    )
    with pytest.raises(ValueError, match="concurrent resource or physical"):
        _ = parse_pack(raw.encode())


def test_oversize_pack_rejected_before_parse() -> None:
    with pytest.raises(ValueError, match="65536 bytes"):
        _ = parse_pack(b" " * 65537)


def test_node_budget_rejects_seventeen_cues() -> None:
    pack = parse_pack(FIXTURE.read_bytes())
    cues = tuple(
        pack.cues[0].model_copy(
            update={"id": f"cue-{i}", "after": (f"cue-{i - 1}",) if i else ()}
        )
        for i in range(17)
    )
    with pytest.raises(ValueError, match="too_long"):
        _ = parse_pack(
            pack.model_copy(update={"cues": cues}).model_dump_json().encode()
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"revision": 4},
        {"resource": "robot"},
        {"capability": "sfx.preset.v1"},
    ],
)
def test_misleading_applied_receipt_rejected(updates: dict[str, str | int]) -> None:
    raw = {
        "status": "applied",
        "cue_id": "hud",
        "capability": "hud.redacted.v1",
        "resource": "hud",
        "owner": "cue",
        "previous_revision": 4,
        "revision": 5,
        "effective": {
            "capability": "hud.redacted.v1",
            "template": "neutral",
            "duration_ms": 100,
        },
        "available": True,
    }
    raw.update(updates)
    with pytest.raises(ValueError, match="ownership"):
        _ = AppliedAck.model_validate(raw)


def test_applied_receipt_retains_ownership_revision() -> None:
    ack = AppliedAck.model_validate_json(
        '{"status":"applied","cue_id":"hud","capability":"hud.redacted.v1","resource":"hud","owner":"cue","previous_revision":4,"revision":5,"effective":{"capability":"hud.redacted.v1","template":"neutral","duration_ms":100},"available":true}'
    )
    assert (ack.owner, ack.revision, ack.effective.duration_ms) == ("cue", 5, 100)


@pytest.mark.parametrize("received", [999, 11001])
def test_receipt_rejects_future_and_stale_occurrence(received: int) -> None:
    with pytest.raises(ValueError, match="freshness"):
        _ = PrivateEvent(
            source="fixture",
            scope="stream",
            stable_id="event",
            causation_id="root",
            origin="adapter",
            occurred_ms=1000,
            received_ms=received,
        )


def test_provider_cannot_supply_event_priority() -> None:
    with pytest.raises(ValueError, match="extra_forbidden"):
        _ = PrivateEvent.model_validate_json(
            '{"source":"fixture","scope":"stream","stable_id":"e","causation_id":"r","origin":"adapter","received_ms":1100,"occurred_ms":1000,"priority":"stop"}'
        )


@pytest.mark.parametrize("capability", ["voice.reserved.v1", "face.reserved.v1"])
def test_reserved_capability_cannot_claim_applied(capability: str) -> None:
    resource = capability.split(".", maxsplit=1)[0]
    raw = {
        "status": "applied",
        "cue_id": "reserved",
        "capability": capability,
        "resource": resource,
        "owner": "cue",
        "previous_revision": 0,
        "revision": 1,
        "effective": {
            "capability": capability,
            "preset": "reserved",
            "duration_ms": 100,
        },
        "available": True,
    }
    with pytest.raises(ValueError, match="ownership"):
        _ = AppliedAck.model_validate(raw)
