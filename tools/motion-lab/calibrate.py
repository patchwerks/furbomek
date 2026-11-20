# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "numpy==1.26.4", "opencv-contrib-python-headless==4.11.0.86",
#   "pydantic==2.12.4", "typer==0.24.1"
# ]
# ///
# How to run from tools/motion-lab: uv run --frozen python calibrate.py --help
"""Private calibration CLI. Exit 0 is observation calibration, never admission."""

import hashlib
import os
import time
from pathlib import Path
from typing import Annotated, assert_never

import typer
from pydantic import ValidationError

from calibration_geometry import CalibrationHoldError
from calibration_images import capture_current, import_images
from calibration_models import CalibrationInput, CalibrationResult
from calibration_solver import calibrate


def main(
    output: Annotated[
        Path,
        typer.Option(help="New private output directory; existing paths are rejected."),
    ],
    source: Annotated[
        Path | None,
        typer.Option(
            "--input", help="Private measured import or explicitly synthetic fixture."
        ),
    ] = None,
    capture: Annotated[
        bool,
        typer.Option(help="Capture only after a complete measured import is supplied."),
    ] = False,
    camera: Annotated[str, typer.Option()] = "Logitech Webcam C930e",
    at_ms: Annotated[
        int | None, typer.Option(help="Deterministic clock for synthetic replay only.")
    ] = None,
) -> None:
    """Recover site calibration and publish a fail-closed private receipt."""
    _ = os.umask(0o077)
    digest = None
    try:
        if output.exists() or output.is_symlink():
            raise CalibrationHoldError("output_already_exists")
        output.mkdir(parents=True, mode=0o700)
        if source is None:
            raise CalibrationHoldError("measured_calibration_prerequisites_missing")
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        data = import_images(CalibrationInput.model_validate_json(raw), source.parent)
        if camera != data.camera:
            raise CalibrationHoldError("camera_identity_changed")
        match data.provenance:
            case "synthetic":
                if capture:
                    raise CalibrationHoldError("capture_requires_measured_import")
            case "measured":
                if at_ms is not None:
                    raise CalibrationHoldError("clock_override_requires_synthetic")
            case unreachable:
                assert_never(unreachable)
        if capture:
            preliminary = calibrate(data, data.current.captured_ms)
            match preliminary.status:
                case "HOLD":
                    raise CalibrationHoldError(preliminary.reasons[0])
                case "CALIBRATED_REPLAY" | "CALIBRATED_OBSERVATION":
                    pass
                case unreachable:
                    assert_never(unreachable)
            current = capture_current(output, data.current)
            data = CalibrationInput.model_validate(
                data.model_dump() | {"current": current.model_dump()}
            )
        now_ms = int(time.time() * 1000) if at_ms is None else at_ms
        result = calibrate(data, now_ms)
        _ = (output / "private-input.json").write_bytes(
            data.model_dump_json(indent=2).encode()
        )
    except CalibrationHoldError as error:
        result = CalibrationResult(
            status="HOLD", reasons=(error.reason,), provenance="unavailable"
        )
    except (OSError, ValidationError) as error:
        result = CalibrationResult(
            status="HOLD",
            reasons=("input_or_output_invalid", type(error).__name__),
            provenance="unavailable",
        )
    result = result.model_copy(update={"input_sha256": digest})
    receipt = result.model_dump_json(indent=2)
    if output.is_dir() and result.reasons != ("output_already_exists",):
        try:
            with (output / "calibration.json").open("x") as handle:
                _ = handle.write(receipt + "\n")
        except OSError as error:
            typer.echo(
                CalibrationResult(
                    status="HOLD",
                    reasons=("receipt_write_failed", type(error).__name__),
                    provenance="unavailable",
                ).model_dump_json()
            )
            raise typer.Exit(2) from error
    typer.echo(receipt)
    match result.status:
        case "HOLD":
            raise typer.Exit(2)
        case "CALIBRATED_REPLAY" | "CALIBRATED_OBSERVATION":
            raise typer.Exit(0)
        case unreachable:
            assert_never(unreachable)


if __name__ == "__main__":
    typer.run(main)
