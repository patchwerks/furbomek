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
        assert cue.ttl_ms == cue.effect.duration_ms
        assert isinstance(cue.effect, (GraphicsEffect, HudEffect, SfxEffect))
    sounds = [cue.effect for cue in pack.cues if isinstance(cue.effect, SfxEffect)]
    assert len(sounds) == 1
    assert 0 < sounds[0].gain_percent <= 30
    assert sounds[0].preset == (
        "liquidation" if name == "liquidation" else "acknowledge"
    )
