from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_feed import SpoolEvent, SpoolPhase
from privacy import (
    PrivacyState,
    apply_privacy_event,
    candidate_allowed,
    complete_candidate,
    mark_uncertain,
    observe_generation,
)


def event(*, phase: SpoolPhase, call: str, shutter: bool = False, release: bool = False) -> SpoolEvent:
    return SpoolEvent(
        kind="tool",
        ts_ms=1_700_000_000_000,
        session="s",
        phase=phase,
        category="BROWSER",
        action="opening",
        detail="example.com",
        call=call,
        shutter=shutter,
        privacy_release=release,
    )


def test_matching_completion_removes_only_its_concurrent_hold() -> None:
    state = PrivacyState.initial(checkpoint_valid=True)
    state = apply_privacy_event(state, event(phase="running", call="a", shutter=True))
    state = apply_privacy_event(state, event(phase="running", call="b"))
    state = apply_privacy_event(state, event(phase="error", call="b"))
    assert {(hold.session, hold.call) for hold in state.holds} == {("s", "a")}
    assert state.latched
    state = apply_privacy_event(state, event(phase="error", call="a", shutter=True))
    assert not state.holds
    assert state.latched


def test_unmatched_completion_and_empty_call_stay_shuttered() -> None:
    state = PrivacyState.initial(checkpoint_valid=True)
    unmatched = apply_privacy_event(state, event(phase="ok", call="missing"))
    assert unmatched.latched
    assert unmatched.uncertain
    empty = apply_privacy_event(state, event(phase="running", call=""))
    assert empty.latched
    assert empty.uncertain


def test_release_requires_fresh_capture_after_dedicated_generation() -> None:
    state = observe_generation(PrivacyState.initial(checkpoint_valid=False), "pid-1")
    assert not candidate_allowed(state)
    state = apply_privacy_event(state, event(phase="running", call="safe"))
    state = apply_privacy_event(state, event(phase="ok", call="safe", release=True))
    assert candidate_allowed(state)
    safe = complete_candidate(state, "pid-1", True)
    assert not safe.latched
    assert not safe.fresh_capture_required


def test_sensitive_latch_has_no_timed_release() -> None:
    state = PrivacyState.initial(checkpoint_valid=True)
    state = apply_privacy_event(state, event(phase="running", call="vault", shutter=True))
    assert state.latched
    assert not candidate_allowed(state)


def test_uncertainty_fact_is_per_poll_but_durable_latch_needs_fresh_generation() -> None:
    state = mark_uncertain(PrivacyState.initial(checkpoint_valid=True))
    state = observe_generation(state, "pid-2")
    assert not candidate_allowed(state)
    state = apply_privacy_event(state, event(phase="running", call="safe"))
    state = apply_privacy_event(state, event(phase="ok", call="safe", release=True))
    assert candidate_allowed(state)
    recovered = complete_candidate(state, "pid-2", True)
    assert not recovered.latched
    held = apply_privacy_event(state, event(phase="running", call="ordinary"))
    assert not candidate_allowed(held)
