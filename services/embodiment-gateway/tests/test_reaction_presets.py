import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

from furbomek_gateway.effect_contracts import (
    GraphicsEffect,
    HudEffect,
    SfxEffect,
)
from furbomek_gateway.reaction_contracts import parse_pack
from furbomek_gateway.reaction_replay import Replay
from furbomek_gateway.reaction_scheduler import ReactionScheduler
from furbomek_gateway.reaction_store import ReactionStore

from .reaction_support import Adapter, Clock
from .test_reaction_store import event

PRESETS: Final = (
    Path(__file__).resolve().parents[3] / "packages/production-contracts/presets"
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("liquidation", [("hud", 1000), ("graphics", 1000), ("sfx", 1000)]),
        ("viewer-reaction", [("hud", 1000), ("sfx", 500)]),
    ],
)
def test_canonical_cli_forecasts_parallel_media_without_dispatch(
    name: str, expected: list[tuple[str, int]]
) -> None:
    command = [
        sys.executable,
        "-m",
        "furbomek_gateway.reaction_replay",
        "--fixture",
        str(PRESETS / f"{name}.json"),
        "--mode",
        "dry-run",
    ]

    completed = subprocess.run(  # noqa: S603 - fixed CLI with repository data
        command, check=True, capture_output=True, text=True, timeout=10
    )

    result = Replay.model_validate_json(completed.stdout)
    assert result.dispatch is False
    assert [
        (row.cue_id, row.start_ms, row.end_ms, row.status, row.dispatch)
        for row in result.timeline
    ] == [(cue, 0, end, "planned_media", False) for cue, end in expected]


@pytest.mark.parametrize("name", ["liquidation", "viewer-reaction"])
def test_canonical_presets_keep_rehearsal_budgets_and_no_physical_authority(
    name: str,
) -> None:
    pack = parse_pack((PRESETS / f"{name}.json").read_bytes())

    assert pack.pack_id == name
    assert pack.horizon_ms <= 1000
    assert pack.priority == "curated"
    for cue in pack.cues:
        assert cue.condition == "capability_available"
        assert cue.on_unavailable == "skip"
        assert cue.on_fault == "cancel_pack"
        assert cue.effect.duration_ms < cue.ttl_ms <= cue.effect.duration_ms + 1000
        assert isinstance(cue.effect, (GraphicsEffect, HudEffect, SfxEffect))
    sounds = [cue.effect for cue in pack.cues if isinstance(cue.effect, SfxEffect)]
    assert len(sounds) == 1
    assert 0 < sounds[0].gain_percent <= 30
    assert sounds[0].preset == (
        "liquidation" if name == "liquidation" else "acknowledge"
    )


@pytest.mark.parametrize(
    ("name", "cue_ids"),
    [("liquidation", ["hud", "graphics", "sfx"]), ("viewer-reaction", ["hud", "sfx"])],
)
@pytest.mark.parametrize("delay_ms", [1, 1000, 1001])
def test_delayed_canonical_scheduler_preserves_duration_expiry_and_dedupe(
    tmp_path: Path, name: str, cue_ids: list[str], delay_ms: int
) -> None:
    pack = parse_pack((PRESETS / f"{name}.json").read_bytes())
    clock, adapter = Clock(), Adapter()
    with ReactionStore(tmp_path / "private" / "state.sqlite") as store:
        scheduler = ReactionScheduler(store, adapter, clock)
        assert scheduler.submit(event(), pack) is not None
        clock.now = delay_ms

        scheduler.tick()

        expected = cue_ids if delay_ms <= 1000 else []
        assert [request.cue.id for request in adapter.requests] == expected
        assert [step.status for step in store.steps()] == [
            "dispatched" if delay_ms <= 1000 else "expired"
        ] * len(cue_ids)
        assert scheduler.submit(event(), pack) is None
        for request in adapter.requests:
            assert scheduler.acknowledge(adapter.ack(request))
        for step in store.steps():
            assert step.end_ms == (
                delay_ms + step.cue.effect.duration_ms if delay_ms <= 1000 else None
            )
        clock.now = delay_ms + 1000
        scheduler.tick()
        assert [step.status for step in store.steps()] == [
            "completed" if delay_ms <= 1000 else "expired"
        ] * len(cue_ids)
        assert [request.cue.id for request in adapter.requests] == expected
        assert all(
            adapter.snapshot(resource).owner is None
            for resource in ("hud", "graphics", "sfx")
        )
