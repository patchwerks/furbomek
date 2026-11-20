import subprocess
import sys
from pathlib import Path

import pytest

from furbomek_gateway.reaction_contracts import parse_pack
from furbomek_gateway.reaction_replay import Replay
from furbomek_gateway.reaction_scheduler import ReactionScheduler
from furbomek_gateway.reaction_store import ReactionStore
from furbomek_gateway.reaction_types import Priority, PropertyState

from .reaction_support import Adapter, Clock
from .test_reaction_store import FIXTURE, event


def test_serial_dependency_waits_for_applied_duration_and_motion_is_locked(
    tmp_path: Path,
) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        assert [r.cue.id for r in adapter.requests] == ["hud", "graphics", "sfx"]
        assert store.steps()[-1].status == "pending"
        for request in adapter.requests:
            assert scheduler.acknowledge(adapter.ack(request))
        clock.now = 1000
        scheduler.tick()
        assert [(s.cue.id, s.status) for s in store.steps()] == [
            ("hud", "completed"),
            ("graphics", "completed"),
            ("sfx", "completed"),
            ("motion", "skipped"),
        ]
        assert store.steps()[-1].reason == "media_only_hold"


@pytest.mark.parametrize("phase", ["reserved", "dispatched", "applied"])
def test_restart_consumes_interrupted_steps_without_retry(
    tmp_path: Path, phase: str
) -> None:
    path = tmp_path / "private" / "state.sqlite"
    clock, adapter = Clock(), Adapter()
    with ReactionStore(path) as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        if phase == "reserved":
            _ = store.reserve(store.steps()[0], adapter.snapshot("hud"))
        else:
            scheduler.tick()
            if phase == "applied":
                _ = scheduler.acknowledge(adapter.ack(adapter.requests[0]))
    count = len(adapter.requests)
    with ReactionStore(path) as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        scheduler.recover()
        scheduler.tick()
        assert len(adapter.requests) == count
        assert all(s.status in ("uncertain", "cancelled") for s in store.steps())
        assert scheduler.submit(event(), parse_pack(FIXTURE.read_bytes())) is None


def test_manual_same_value_revision_revokes_restore_and_late_ack(
    tmp_path: Path,
) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        request = adapter.requests[0]
        ack = adapter.ack(request)
        operator = adapter.snapshot("hud").model_copy(
            update={"owner": "operator", "revision": 2}
        )
        adapter.states["hud"] = operator
        assert not scheduler.acknowledge(ack)
        clock.now = 1001
        scheduler.tick()
        assert adapter.snapshot("hud") == operator


def test_live_loss_cancels_consumed_work_and_reports_hold(tmp_path: Path) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        adapter.ready = False
        scheduler.tick()
        assert all(s.status in ("uncertain", "cancelled") for s in store.steps())
        assert all(s.reason == "media_only_hold" for s in store.steps())


def test_late_tick_does_not_start_expired_cues(tmp_path: Path) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        clock.now = 11000
        scheduler.tick()
        assert adapter.requests == []
        assert all(s.status == "expired" for s in store.steps())


def test_priority_preempts_curated_but_not_owner(tmp_path: Path) -> None:

    clock, adapter = Clock(), Adapter()
    pack = parse_pack(FIXTURE.read_bytes())
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        low = scheduler.submit(event(), pack)
        scheduler.tick()
        _ = scheduler.submit_trusted(event("owner"), pack, Priority.OWNER)
        _ = scheduler.submit_trusted(event("hermes"), pack, Priority.ADMITTED)
        scheduler.tick()
        assert all(s.reason == "preempted" for s in store.steps() if s.event_id == low)
        assert [r.owner for r in adapter.requests] == [
            "r1-s0",
            "r1-s1",
            "r1-s2",
            "r2-s0",
            "r2-s1",
            "r2-s2",
        ]
        clock.now = 1
        scheduler.tick()
        assert all(
            s.status == "expired"
            for s in store.steps()
            if s.event_id == 3 and not s.cue.after
        )


def test_ack_duplicate_mismatch_and_cancel_cannot_change_new_owner(
    tmp_path: Path,
) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        identity = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        ack = adapter.ack(adapter.requests[0])
        assert not scheduler.acknowledge(ack.model_copy(update={"cue_id": "wrong"}))
        assert scheduler.acknowledge(ack)
        assert not scheduler.acknowledge(ack)
        assert identity is not None
        scheduler.cancel(identity)
        assert not scheduler.acknowledge(ack)
        assert adapter.snapshot("hud").owner is None


def test_stop_is_unconditional_and_disables_new_admission(tmp_path: Path) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        scheduler.stop()
        assert adapter.stops == 1
        assert scheduler.submit(event("new"), parse_pack(FIXTURE.read_bytes())) is None
        assert all(s.status in ("uncertain", "cancelled") for s in store.steps())


def test_dry_run_cli_is_deterministic_and_never_dispatches() -> None:

    command = [
        sys.executable,
        "-m",
        "furbomek_gateway.reaction_replay",
        "--fixture",
        str(FIXTURE),
        "--mode",
        "dry-run",
    ]
    first = subprocess.run(command, check=True, capture_output=True, text=True)  # noqa: S603 - fixed module and repository fixture
    second = subprocess.run(command, check=True, capture_output=True, text=True)  # noqa: S603 - fixed module and repository fixture
    assert first.stdout == second.stdout
    result = Replay.model_validate_json(first.stdout)
    assert result.dispatch is False
    assert [
        (row.cue_id, row.start_ms, row.status, row.dispatch) for row in result.timeline
    ] == [
        ("hud", 0, "planned_media", False),
        ("graphics", 0, "planned_media", False),
        ("sfx", 0, "planned_media", False),
        ("motion", 1000, "media_only_hold", False),
    ]
    rejected = subprocess.run(  # noqa: S603 - fixed invalid CLI mode
        [*command[:-1], "live"], check=False, capture_output=True, text=True
    )
    assert rejected.returncode == 2


@pytest.mark.parametrize("overwrite", [False, True])
def test_applied_expiry_restores_only_matching_owner_revision(
    tmp_path: Path, overwrite: bool
) -> None:

    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        request = adapter.requests[1]
        assert scheduler.acknowledge(adapter.ack(request))
        if overwrite:
            adapter.states["graphics"] = PropertyState(
                resource="graphics",
                owner="operator",
                revision=2,
                effect=request.cue.effect,
            )
        clock.now = 1000
        scheduler.tick()
        current = adapter.snapshot("graphics")
        assert current.owner == ("operator" if overwrite else None)
        assert current.effect == (request.cue.effect if overwrite else None)


def test_conflicting_sfx_and_graphics_wait_within_explicit_ttl(tmp_path: Path) -> None:
    clock, adapter = Clock(), Adapter()
    pack = parse_pack(FIXTURE.read_bytes())
    pack = pack.model_copy(
        update={"cues": tuple(c.model_copy(update={"ttl_ms": 2000}) for c in pack.cues)}
    )
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), pack)
        _ = scheduler.submit(event("two"), pack)
        scheduler.tick()
        assert [r.owner for r in adapter.requests] == ["r1-s0", "r1-s1", "r1-s2"]
        for request in adapter.requests:
            assert scheduler.acknowledge(adapter.ack(request))
        clock.now = 1000
        scheduler.tick()
        assert [r.owner for r in adapter.requests] == [
            "r1-s0",
            "r1-s1",
            "r1-s2",
            "r2-s0",
            "r2-s1",
            "r2-s2",
        ]


def test_replayed_event_order_produces_same_receipt_sequence(tmp_path: Path) -> None:
    expected = [("r1-s0", "hud"), ("r1-s1", "graphics"), ("r1-s2", "sfx")]
    for run in ("first", "replay"):
        adapter, clock = Adapter(), Clock()
        with ReactionStore(tmp_path / run / "state.sqlite") as store:
            scheduler = ReactionScheduler(store, adapter, clock)
            for identity in ("one", "one"):
                _ = scheduler.submit(event(identity), parse_pack(FIXTURE.read_bytes()))
            scheduler.tick()
            receipts = [adapter.ack(request) for request in adapter.requests]
            assert [(ack.owner, ack.cue_id) for ack in receipts] == expected
            assert all(scheduler.acknowledge(ack) for ack in receipts)
