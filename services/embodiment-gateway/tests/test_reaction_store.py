from pathlib import Path

import pytest

from furbomek_gateway.reaction_contracts import PrivateEvent, parse_pack
from furbomek_gateway.reaction_scheduler import ReactionScheduler
from furbomek_gateway.reaction_store import ReactionStore
from furbomek_gateway.reaction_types import (
    AdapterFaultError,
    Priority,
    Reservation,
    StorePrivacyError,
)

from .reaction_support import Adapter, Clock

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "packages/production-contracts/fixtures/liquidation.json"
)


def event(identity: str = "one") -> PrivateEvent:
    return PrivateEvent(
        source="fixture",
        scope="stream",
        stable_id=identity,
        causation_id="root",
        origin="adapter",
        occurred_ms=1000,
        received_ms=1000,
    )


def test_admission_is_durable_and_duplicate_pack_cannot_repeat(tmp_path: Path) -> None:
    path = tmp_path / "private" / "reactions.sqlite"
    with ReactionStore(path) as store:
        first = store.admit(
            event(),
            parse_pack(FIXTURE.read_bytes()),
            Reservation(now_ms=0, age_budget_ms=10000, priority=Priority.CURATED),
        )
    with ReactionStore(path) as store:
        second = store.admit(
            event(),
            parse_pack(FIXTURE.read_bytes()),
            Reservation(now_ms=1, age_budget_ms=9999, priority=Priority.CURATED),
        )
        assert first is not None
        assert second is None
        assert len(store.steps()) == 4
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_two_connections_cannot_reserve_same_resource(tmp_path: Path) -> None:
    path = tmp_path / "private" / "reactions.sqlite"
    with ReactionStore(path) as left, ReactionStore(path) as right:
        pack = parse_pack(FIXTURE.read_bytes())
        for identity in ("one", "two"):
            _ = left.admit(
                event(identity),
                pack,
                Reservation(now_ms=0, age_budget_ms=10000, priority=Priority.CURATED),
            )
        first, second = [step for step in left.steps() if step.cue.id == "hud"]
        assert left.reserve(first, None)
        assert not right.reserve(second, None)


def test_rejects_public_directory_and_symlink(tmp_path: Path) -> None:

    tmp_path.chmod(0o755)
    with pytest.raises(StorePrivacyError), ReactionStore(tmp_path / "state.sqlite"):
        pass
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    (private / "state.sqlite").symlink_to(tmp_path / "outside")
    with (
        pytest.raises(OSError, match="Too many levels"),
        ReactionStore(private / "state.sqlite"),
    ):
        pass


def test_dedupe_prunes_only_after_retention_and_terminal_steps(tmp_path: Path) -> None:
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        _ = store.admit(
            event(),
            parse_pack(FIXTURE.read_bytes()),
            Reservation(now_ms=0, age_budget_ms=10000, priority=Priority.CURATED),
        )
        assert store.prune(100000) == 0
        for step in store.steps():
            assert store.transition(
                step, step.model_copy(update={"status": "cancelled"})
            )
        assert store.prune(61000) == 0
        assert store.prune(61001) == 1


def test_scheduler_excludes_second_owner(tmp_path: Path) -> None:

    path = tmp_path / "private" / "state.sqlite"
    with ReactionStore(path) as first, ReactionStore(path) as second:
        first.claim_scheduler()
        with pytest.raises(BlockingIOError):
            second.claim_scheduler()


def test_terminal_step_cannot_be_reserved_again(tmp_path: Path) -> None:
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        _ = store.admit(
            event(),
            parse_pack(FIXTURE.read_bytes()),
            Reservation(now_ms=0, age_budget_ms=10000, priority=Priority.CURATED),
        )
        step = store.steps()[0]
        cancelled = step.model_copy(update={"status": "cancelled"})
        assert store.transition(step, cancelled)
        assert not store.reserve(cancelled, None)


@pytest.mark.parametrize("phase", ["reserved", "dispatched"])
def test_physical_crash_gap_is_consumed_and_stopped(tmp_path: Path, phase: str) -> None:

    path = tmp_path / "private" / "state.sqlite"
    adapter = Adapter()
    with ReactionStore(path) as store:
        _ = store.admit(
            event(),
            parse_pack(FIXTURE.read_bytes()),
            Reservation(now_ms=0, age_budget_ms=10000, priority=Priority.ADMITTED),
        )
        motion = store.steps()[-1]
        assert store.reserve(motion, adapter.snapshot("robot"))
        if phase == "dispatched":
            reserved = store.steps()[-1]
            assert store.transition(
                reserved, reserved.model_copy(update={"status": "dispatched"})
            )
    with ReactionStore(path) as store:
        scheduler = ReactionScheduler(store, adapter, Clock())
        scheduler.tick()
        assert store.steps()[-1].status == "uncertain"
        assert adapter.stops == 1
        assert adapter.requests == []


def test_restart_reconciles_crash_after_consumption_before_release(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private" / "state.sqlite"
    adapter, clock = Adapter(), Clock()
    with ReactionStore(path) as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        scheduler.tick()
        assert scheduler.acknowledge(adapter.ack(adapter.requests[0]))
        step = store.steps()[0]
        assert store.transition(step, step.model_copy(update={"status": "uncertain"}))
    with ReactionStore(path) as store:
        _ = ReactionScheduler(store, adapter, clock)
        assert adapter.snapshot("hud").effect is None
        assert store.steps()[0].status == "uncertain"


def test_projection_excludes_identity_and_arbitrary_cancel_reason(
    tmp_path: Path,
) -> None:
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        identity = scheduler.submit(
            event("private-provider-id"), parse_pack(FIXTURE.read_bytes())
        )
        assert identity is not None
        scheduler.cancel(identity, "sensitive-provider-text")
        assert [row.model_dump() for row in scheduler.projection()] == [
            {"resource": resource, "status": "cancelled", "media_only_hold": False}
            for resource in ("hud", "graphics", "sfx", "robot")
        ]


def test_dispatch_fault_consumes_graph_without_retries(tmp_path: Path) -> None:
    adapter, clock = Adapter(), Clock()
    adapter.fault = True
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        _ = scheduler.submit(event(), parse_pack(FIXTURE.read_bytes()))
        with pytest.raises(AdapterFaultError):
            scheduler.tick()
        scheduler.tick()
        assert len(adapter.requests) == 1
        assert [step.status for step in store.steps()] == [
            "uncertain",
            "cancelled",
            "cancelled",
            "cancelled",
        ]
        assert adapter.snapshot("hud").owner is None
