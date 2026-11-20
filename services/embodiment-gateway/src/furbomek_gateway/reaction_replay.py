"""Offline finite timeline compiler; dry-run never instantiates an output adapter."""

import json
from pathlib import Path
from typing import Annotated, Literal

import typer

from .effect_contracts import Contract, capability_definition
from .reaction_contracts import parse_pack


class PreviewCue(Contract):
    """Prediction only: no claim that a renderer applied or a robot moved."""

    cue_id: str
    start_ms: int
    end_ms: int
    status: Literal["planned_media", "media_only_hold"]
    dispatch: Literal[False] = False


class Replay(Contract):
    """Redacted deterministic fixture output, with no provider identities."""

    mode: Literal["dry-run"] = "dry-run"
    dispatch: Literal[False] = False
    timeline: tuple[PreviewCue, ...]


def replay(fixture: Path) -> Replay:
    """Compile the authoritative typed DAG using stable input cue ordering."""
    pack = parse_pack(fixture.read_bytes())
    ends: dict[str, int] = {}
    result: dict[str, PreviewCue] = {}
    pending = list(pack.cues)
    while pending:
        ready = [cue for cue in pending if set(cue.after) <= ends.keys()]
        for cue in ready:
            start = max((ends[key] for key in cue.after), default=0)
            definition = capability_definition(cue.effect.capability)
            status = (
                "planned_media"
                if definition.available and not definition.physical
                else "media_only_hold"
            )
            ends[cue.id] = start + cue.effect.duration_ms
            result[cue.id] = PreviewCue(
                cue_id=cue.id, start_ms=start, end_ms=ends[cue.id], status=status
            )
            pending.remove(cue)
    return Replay(timeline=tuple(result[cue.id] for cue in pack.cues))


def main(
    fixture: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    mode: Annotated[str, typer.Option()] = "dry-run",
) -> None:
    """Export an offline predicted timeline. Live execution is not a CLI mode."""
    if mode != "dry-run":
        msg = "only dry-run is supported"
        raise typer.BadParameter(msg)
    typer.echo(json.dumps(replay(fixture).model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    typer.run(main)
