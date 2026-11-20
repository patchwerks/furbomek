"""Safe executable trial boundary; physical flags fail before reading paths."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from trials_models import CatalogReceipt, TrialManifest


def run_cli(replay_catalog: Callable[[TrialManifest, Path], CatalogReceipt]) -> None:
    """Emit a bounded typed receipt; no serial, camera or gateway I/O exists."""

    def main(
        replay: Annotated[Path | None, typer.Option()] = None,
        run_approved: Annotated[Path | None, typer.Option()] = None,
    ) -> None:
        if run_approved is not None:
            result = CatalogReceipt(
                status="HOLD",
                reasons=(
                    "physical_dispatch_unavailable",
                    "calibrated_stage_and_independent_cutoff_required",
                ),
            )
        elif replay is None:
            result = CatalogReceipt(
                status="HOLD", reasons=("replay_or_approval_missing",)
            )
        else:
            try:
                data = TrialManifest.model_validate_json(replay.read_bytes())
                result = replay_catalog(data, replay.parent)
            except (OSError, ValidationError) as error:
                result = CatalogReceipt(
                    status="HOLD",
                    reasons=(
                        "invalid_trial_manifest",
                        type(error).__name__,
                    ),
                )
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(2 if result.status == "HOLD" else 0)

    typer.run(main)
