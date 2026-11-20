"""Replay transport and actual image provenance, independent of pasted corners."""

import hashlib
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from score import score_run
from score_models import ScoreInput, ScoreResult, UncalibratedRecording
from tests.score_fixture import replay, write_replay
from tests.test_score import movement


@pytest.mark.parametrize("calibrated", [True, False])
def test_cli_observable_or_unmeasurable(tmp_path: Path, *, calibrated: bool) -> None:
    manifest = tmp_path / "reference-run.json"
    if calibrated:
        write_replay(manifest, replay(movement(x=20)))
    else:
        image = tmp_path / "untagged.png"
        assert cv2.imwrite(str(image), np.full((480, 640, 3), 120, dtype=np.uint8))
        recording = UncalibratedRecording(
            schema_version=1,
            calibration=None,
            provenance="measured",
            recording_file=image.name,
            recording_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        )
        _ = manifest.write_text(recording.model_dump_json())
    process = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "score.py"),
            "--replay",
            str(manifest),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    result = ScoreResult.model_validate_json(process.stdout)
    assert process.returncode == (0 if calibrated else 2), process.stderr
    assert result.outcome == ("motion" if calibrated else "unmeasurable")
    if not calibrated:
        assert result.reasons == ("calibration_unavailable",)
        assert result.metrics is None


@pytest.mark.parametrize("tampered", [True, False])
def test_loss_image_bytes_override_claimed_markers(
    tmp_path: Path, *, tampered: bool
) -> None:
    data = replay(movement(x=20))
    image = tmp_path / "unmarked.png"
    assert cv2.imwrite(str(image), np.full((480, 640), 150, dtype=np.uint8))
    raw = data.model_dump()
    frame = raw["frames"][4]
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    frame["content_sha256"] = "0" * 64 if tampered else digest
    frame["observation"]["image_file"] = image.name
    frame["observation"]["image_sha256"] = frame["content_sha256"]
    result = score_run(ScoreInput.model_validate(raw), tmp_path)
    assert result.outcome == "unmeasurable"
    assert result.reasons == (
        ("image_digest_mismatch" if tampered else "no_decoded_tags"),
    )


def test_cli_loss_malformed_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "invalid.json"
    _ = manifest.write_text('{"schema_version":99}')
    process = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "score.py"),
            "--replay",
            str(manifest),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    result = ScoreResult.model_validate_json(process.stdout)
    assert process.returncode == 2
    assert result.reasons == ("invalid_replay_manifest", "ValidationError")
