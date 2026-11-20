# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "numpy==1.26.4", "opencv-contrib-python-headless==4.11.0.86",
#   "pydantic==2.12.4", "typer==0.24.1"
# ]
# ///
# How to run from tools/motion-lab: uv run --frozen python stage.py --help
"""Verify private stage evidence offline; no capture, actuator or release authority."""

import time
from pathlib import Path
from typing import Annotated, assert_never

import typer
from pydantic import ValidationError

from calibration_geometry import CalibrationHoldError
from stage_gateway import StageReceipt
from stage_verification import StageBundle, verify_bundle


def main(
    verify: Annotated[
        Path,
        typer.Option(
            help="Private stage bundle or named synthetic comparison fixture."
        ),
    ],
    at_ms: Annotated[
        int | None, typer.Option(help="Clock override only for named synthetic replay.")
    ] = None,
) -> None:
    """Print a machine-readable receipt; 0 means replay eligibility, never release."""
    try:
        bundle = StageBundle.model_validate_json(verify.read_bytes())
        match bundle.calibration_input.provenance:
            case "synthetic":
                if (
                    bundle.request.mode != "replay_comparison"
                    or bundle.request.comparison_id is None
                ):
                    raise CalibrationHoldError("synthetic_requires_named_replay")
            case "measured":
                if at_ms is not None:
                    raise CalibrationHoldError("clock_override_requires_synthetic")
            case unreachable:
                assert_never(unreachable)
        result = verify_bundle(
            bundle, verify.parent, int(time.time() * 1000) if at_ms is None else at_ms
        )
    except CalibrationHoldError as error:
        result = StageReceipt(
            status="HOLD", local_checks_passed=False, reasons=(error.reason,)
        )
    except (OSError, ValidationError):
        result = StageReceipt(
            status="HOLD",
            local_checks_passed=False,
            reasons=("stage_evidence_missing_or_invalid",),
        )
    typer.echo(result.model_dump_json())
    match result.status:
        case "REPLAY_ELIGIBLE":
            raise typer.Exit(0)
        case "HOLD":
            raise typer.Exit(2)
        case unreachable:
            assert_never(unreachable)


if __name__ == "__main__":
    typer.run(main)
