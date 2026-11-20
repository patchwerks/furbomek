"""Replay command boundary; imported only by the executable scoring entrypoint."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, assert_never

import typer
from pydantic import TypeAdapter, ValidationError

from score_models import ScoreInput, ScoreResult, UncalibratedRecording


def run_cli(scorer: Callable[[ScoreInput, Path], ScoreResult]) -> None:
    """Keep CLI dependency loading outside the scoring library import surface."""

    def main(
        replay: Annotated[
            Path, typer.Option(help="Private or synthetic replay manifest.")
        ],
    ) -> None:
        """Emit a typed audit receipt; no input opens live resources."""
        try:
            data = TypeAdapter[ScoreInput | UncalibratedRecording](
                ScoreInput | UncalibratedRecording
            ).validate_json(replay.read_bytes())
            match data:
                case ScoreInput():
                    result = scorer(data, replay.parent)
                case UncalibratedRecording():
                    recording = replay.parent / data.recording_file
                    verified = (
                        not recording.is_symlink()
                        and hashlib.sha256(recording.read_bytes()).hexdigest()
                        == data.recording_sha256
                    )
                    result = ScoreResult(
                        outcome="unmeasurable",
                        motion_kind="unmeasurable",
                        provenance="measured",
                        reasons=(
                            "calibration_unavailable"
                            if verified
                            else "recording_digest_mismatch",
                        ),
                        recording_sha256=data.recording_sha256,
                    )
                case unreachable:
                    assert_never(unreachable)
        except (OSError, ValidationError) as error:
            result = ScoreResult(
                outcome="unmeasurable",
                motion_kind="unmeasurable",
                reasons=("invalid_replay_manifest", type(error).__name__),
                provenance="unavailable",
            )
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(2 if result.outcome == "unmeasurable" else 0)

    typer.run(main)
