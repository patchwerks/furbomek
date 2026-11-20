"""Behavior at the pure policy and persisted JSON boundaries."""

import json

import pytest
from pydantic import ValidationError

from furbomek_gateway.framing_models import (
    Frame,
    FramingPreset,
    Manual,
    Roi,
    Rule,
    Signal,
    Subject,
    Trigger,
)
from furbomek_gateway.framing_policy import FramingPolicy
from furbomek_gateway.framing_presets import Presets

from .framing_cases import PERSON, ROBOT, frame, preset


def test_dwell_pan_release_return() -> None:
    policy = FramingPolicy(preset())
    decisions = [
        policy.step(frame(t, event=e))
        for t, e in [
            (0, False),
            (100, True),
            (599, True),
            (600, True),
            (1599, False),
            (1600, False),
        ]
    ]
    assert [d.target.id for d in decisions] == [
        "robot",
        "robot",
        "robot",
        "host",
        "host",
        "robot",
    ]
    assert decisions[3].reason == "qualified"
    assert decisions[-1].reason == "default"


@pytest.mark.parametrize(
    "change",
    [
        {"source": "chat"},
        {"at_ms": 0},
        {"at_ms": 3000},
        {"confidence": 0.2},
        {"subject": Subject(kind="person", id="stranger")},
        {"kind": "observation"},
        {"event": "reaction"},
    ],
)
def test_unqualified_input_cannot_select_target(
    change: dict[str, str | int | float | Subject],
) -> None:
    policy = FramingPolicy(preset())
    signal = Signal(
        kind="event", source="broker", subject=PERSON, at_ms=2000, confidence=1.0
    )
    changed = Signal.model_validate(signal.model_dump() | change)
    decisions = [
        policy.step(Frame(now_ms=t, signals=(*frame(t).signals, changed)))
        for t in (2000, 2500)
    ]
    assert [d.target.id for d in decisions] == ["robot", "robot"]


def test_brief_loss_holds_then_falls_back_without_unrelated_detection() -> None:
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    brief = policy.step(frame(999, robot=False))
    lost = policy.step(frame(1000, robot=False))
    assert (brief.target.id, brief.reason, brief.hold_previous) == (
        "robot",
        "loss_hold",
        True,
    )
    assert (lost.target.id, lost.reason) == ("wide", "fallback")


def test_interrupted_and_missing_samples_restart_dwell() -> None:
    policy = FramingPolicy(preset())
    decisions = [
        policy.step(frame(t, event=e))
        for t, e in [
            (0, True),
            (400, False),
            (500, True),
            (999, True),
            (2001, True),
            (2500, True),
            (2501, True),
        ]
    ]
    assert [d.target.id for d in decisions] == ["robot"] * 6 + ["host"]


def test_transient_trigger_loss_and_same_priority_stay_stable() -> None:
    config = preset()
    rival = Rule(
        id="aaa",
        target="wide",
        priority=10,
        trigger=Trigger(kind="observation", source="tracker", subject=ROBOT),
    )
    policy = FramingPolicy(
        FramingPreset.model_validate(
            config.model_dump() | {"rules": (*config.rules, rival)}
        )
    )
    _ = policy.step(frame(0, event=True, robot=False))
    _ = policy.step(frame(500, event=True, robot=False))
    decisions = [
        policy.step(frame(t, event=e))
        for t, e in [(1000, False), (1500, True), (2000, True)]
    ]
    assert [d.target.id for d in decisions] == ["host"] * 3


def test_higher_priority_waits_for_minimum_shot() -> None:
    config = preset()
    rival = Rule(
        id="urgent",
        target="wide",
        priority=20,
        trigger=Trigger(kind="observation", source="tracker", subject=ROBOT),
    )
    policy = FramingPolicy(
        FramingPreset.model_validate(
            config.model_dump() | {"rules": (*config.rules, rival)}
        )
    )
    _ = policy.step(frame(0, event=True, robot=False))
    _ = policy.step(frame(500, event=True, robot=False))
    decisions = [policy.step(frame(t, event=True)) for t in (600, 1100, 1500)]
    assert [d.target.id for d in decisions] == ["host", "host", "wide"]


def test_manual_override_survives_events_then_reset() -> None:
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    policy.override(Manual(target="wide", duration_ms=5000))
    decisions = [policy.step(frame(t, event=True)) for t in (100, 1000, 4000)]
    assert [(d.target.id, d.reason) for d in decisions] == [("wide", "manual")] * 3
    assert policy.reset(frame(4001)).target.id == "robot"


def test_manual_expiry_does_not_inherit_trigger_dwell() -> None:
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    policy.override(Manual(target="wide", duration_ms=1000))
    _ = policy.step(frame(500, event=True))
    assert policy.step(frame(1000, event=True)).target.id == "robot"


def test_expiry_and_clock_reversal_fail_closed() -> None:
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    assert policy.step(frame(30000, event=True)).reason == "expired"
    with pytest.raises(ValueError, match="backwards"):
        _ = policy.step(frame(29999))


@pytest.mark.parametrize(
    "change",
    [
        {"default": "unknown"},
        {"fallback": "host"},
        {"ttl_ms": 600001},
        {"hold_ms": "100"},
        {"expression": "chat.contains('pan')"},
        {"tracking_source": "https://example.com"},
        {"schema_version": "v2"},
        {"transition": {"zoom": 5.0}},
    ],
)
def test_malformed_presets_rejected(
    change: dict[str, str | int | dict[str, float]],
) -> None:
    with pytest.raises(ValidationError):
        _ = FramingPreset.model_validate(preset().model_dump() | change)


def test_roi_unknown_rule_subject_and_override_rejected() -> None:
    with pytest.raises(ValidationError):
        _ = Roi(x=0.9, y=0.0, width=0.2, height=1.0)
    config = preset().model_dump()
    config["rules"][0]["trigger"]["subject"]["id"] = "unknown"
    with pytest.raises(ValidationError):
        _ = FramingPreset.model_validate(config)
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    with pytest.raises(ValueError, match="approved"):
        policy.override(Manual(target="unknown", duration_ms=10))


def test_persistence_preserves_types_without_runtime_state() -> None:
    saved = Presets(presets=(preset(),)).save()
    restored = Presets.load(saved).presets[0]
    assert restored == preset()
    assert FramingPolicy(restored).step(frame(0)).target.id == "robot"
    with pytest.raises(ValueError, match="duplicate"):
        _ = Presets.load(b'{"presets":[],"presets":[]}')
    with pytest.raises(ValidationError):
        _ = Presets.load(json.dumps({"presets": [], "manual": "host"}).encode())


def test_output_freshness_is_milliseconds_and_reset_cannot_extend_lease() -> None:
    policy = FramingPolicy(preset())
    decision = policy.step(frame(1000))
    assert decision.expires_ms == 1300
    assert policy.reset(frame(31000)).reason == "expired"


def test_observation_rule_cannot_override_camera_freshness_bound() -> None:
    config = preset()
    rule = Rule(
        id="seen",
        target="host",
        priority=10,
        dwell_ms=0,
        trigger=Trigger(
            kind="observation", source="tracker", subject=PERSON, max_age_ms=10000
        ),
    )
    policy = FramingPolicy(
        FramingPreset.model_validate(config.model_dump() | {"rules": (rule,)})
    )
    old = Signal(
        kind="observation", source="tracker", subject=PERSON, at_ms=0, confidence=1.0
    )
    decision = policy.step(Frame(now_ms=601, signals=(old,)))
    assert (decision.target.id, decision.rule) == ("wide", None)


@pytest.mark.parametrize("change", [{"lock_age_ms": 601}, {"output_ttl_ms": 601}])
def test_camera_and_output_bounds_reject_over_600ms(change: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        _ = FramingPreset.model_validate(preset().model_dump() | change)


def test_restore_does_not_restore_active_pan_or_override() -> None:
    config = preset()
    policy = FramingPolicy(config)
    _ = policy.step(frame(0, event=True))
    assert policy.step(frame(500, event=True)).target.id == "host"
    policy.override(Manual(target="wide", duration_ms=5000))
    restored = Presets.load(Presets(presets=(policy.preset,)).save()).presets[0]
    assert FramingPolicy(restored).step(frame(0)).target.id == "robot"


def test_fixed_override_invalidates_previous_crop_hold() -> None:
    policy = FramingPolicy(preset())
    _ = policy.step(frame(0))
    policy.override(Manual(target="wide", duration_ms=100))
    _ = policy.step(frame(10))
    result = policy.step(frame(100, robot=False))
    assert (result.target.id, result.hold_previous) == ("wide", False)
