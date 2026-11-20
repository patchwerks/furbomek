---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-04
author: Codex
status: active
---
# Calibrated replay scoring v1

**Observed software replay only.** The scorer reads recordings; it neither opens
cameras nor sends robot commands. The current private unmarked C930e recording
has no measured calibration and returns `unmeasurable`. Synthetic fixtures are
independent analytic Brown projections of a dimensioned 40 mm marker at surveyed
positions and heights; their accuracy is not a physical qualification claim.

The [calibration contract](README.md) and [portable qualification rubric](../../docs/hardware/motion-profiles/QUALIFICATION.md)
remain authoritative. Neither a score, a Guard ACK nor a `completed`/`disarmed`
wire status authorizes motion. `physical_motion_authorized` is always false.

## Consumer API

From a Python process with `tools/motion-lab` on its module path, parse external
JSON using `score_models.ScoreInput.model_validate_json(bytes)` and call
`score.score_run(data, manifest_directory) -> score_models.ScoreResult`.
The v1 CLI takes the same manifest. Exit 0 means a scored optical observation,
including `partial`, `unexpected` and `no_travel`; exit 2 means `unmeasurable`.
Consumers must inspect the outcome, provenance, reasons and independent Guard
status. Neither exit status alone nor `motion` is a safety admission decision.

```sh
uv run --frozen --project tools/motion-lab python tools/motion-lab/score.py \
  --replay tools/motion-lab/fixtures/score-forward.json
uv run --frozen --project tools/motion-lab pytest -q \
  tools/motion-lab/tests/test_score.py -k 'observable or loss or uncertainty'
```

A complete example is [score-forward.json](fixtures/score-forward.json). Keep real
manifests/images/receipts outside Git under a mode-0700 directory, with files
mode 0600. The CLI emits JSON on stdout and never overwrites artifacts. The
versioned immutable schema forbids extra fields and nonfinite numeric values.
Task 8 can create one manifest per isolated trial phase; Task 11 can consume the
result but must perform its own fresh observation and physical admission gates.
This offline implementation refits calibration per frame and is not a realtime
observer. Long phases should be scored after collection, not on a dispatch path.

## Geometry and provenance

`calibration` embeds the original Task 5 measured import or explicit synthetic
fixture, with a separate `calibration_id`. The result's `calibration_sha256` hashes
the canonical parsed calibration JSON. `camera_frame_sha256` retains each camera
image digest independently. Real imports decode same-directory, hash-bound PNGs;
pasted corners cannot override the actual pixels. Synthetic corner-only fixtures
are explicitly marked synthetic. Camera, board, marker identity, full boundary,
foot visibility, contact, reference drift and validated region/height checks run
for every frame. A single invalid frame invalidates the entire phase; samples
are never silently dropped or interpolated across a loss.

The target must be rigid and parallel to the chassis reference plane. Task 5's
board coordinates have X right, Y down and Z into the board.
`marker_x_to_body_forward_deg` is the independently surveyed angle from the
marker's X axis to chassis forward, positive about board Z. The initial marker
yaw plus this offset defines body forward. The scorer rotates planar displacement
onto forward, negates its perpendicular axis for left, negates board yaw change
for counterclockwise yaw, and negates Z change for height up. This supports
arbitrary starting heading without binding a robot profile to a camera or stage.
Mount offset is operator survey evidence, not a value inferred from an ACK.

Height change is a separate posture metric. Translation, turn, posture, mixed,
and stationary kinds remain separate from motion/partial/unexpected/no-travel
outcomes. Unmeasurable results have an unmeasurable kind and no metrics. Tilt
outside Task 5's parallel-target allowance is unmeasurable; this scorer does not
claim roll/pitch qualification. A copied marker with the same ID is not
cryptographically identifiable. Physical mounting and surveyed identity remain
prerequisites; wrong or missing decoded IDs are rejected.

## Time and conservative error bounds

All phase timestamps, receipt times, calibration validity and clock anchors use
one named **local monotonic** millisecond clock. Camera PTS uses a separate origin.
At least three independently obtained PTS/monotonic anchor pairs must span all
frames. Endpoints define the affine projection; interior residual, anchor
measurement uncertainty and Guard timestamp uncertainty are added. Drift above
1000 ppm, total uncertainty above the configured maximum (at most 100 ms),
extrapolation, nonmonotonic anchors and mismatched clock IDs hold. These labels
and anchors must come from the recorder; no source timestamp is assumed to be a
local monotonic timestamp. Task 5 `captured_ms` remains archival metadata and is
not used as a substitute for this validated projection.

Frames require consecutive sequence numbers, increasing PTS and distinct content
digests. The complete session/command/phase triple must match the Guard record.
Receipt delay is bounded, inter-frame gaps over 150 ms hold, and the first two
frames must bracket phase start with uncertainty. A post-stop tail must cover
`observed_until_ms`; every capture's complete uncertainty interval must lie inside
calibration validity. The validity interval is a recorder assertion and must be
revoked when the calibrated view changes. Board image drift also independently
rejects a changed view; globally moving camera and board together can be invisible.

Each metric includes a unit and conservative absolute uncertainty, not a
statistical confidence interval. Relative spatial/yaw bounds add both endpoint
calibration errors. Planar coordinates add initial-heading uncertainty; observed
peak speed times the timing bound adds timestamp error. Bounds exceeding 5 mm,
2 degrees, or one quarter of any nonzero expected axis hold. These bounds and
peak excursion describe **sampled observations**, not unobserved motion between
frames. They cannot replace independent stopping-distance/cutoff measurement.

Expected signed displacement and tolerances are predeclared. Wrong direction at
any sampled point or motion on an expected zero axis yields `unexpected`. No
excursion above uncertainty yields `no_travel`, including a nonfinal Guard phase.
A smaller displacement or missing stable tail yields `partial`. Post-stop
settling requires every remaining pose to stay within the error bound for at
least the predeclared window (minimum 200 ms), with timestamp margins. The settle
time uncertainty includes one frame interval. `post_stop_excursion` starts at
the last sample before STOP, conservatively retaining the bracketing movement.

`slip_evidence: post_stop_drift` reports observed planar drift after that bracket.
It is a diagnostic cue, not proof of foot slip or physical actuator cutoff.
Otherwise slip remains `unmeasurable`; chassis tags cannot distinguish successful
traction from every slip mechanism. Alpha, IR and tracker outputs provide no
independent safety evidence here.

## Footage without calibration

The CLI also accepts `UncalibratedRecording`: `schema_version: 1`,
`calibration: null`, `provenance: measured`, a same-directory `recording_file`
(`.mkv` or `.png`) and `recording_sha256`. It verifies the bytes and returns
`calibration_unavailable` with no fabricated geometry, Guard phase or timestamps.
It does not claim to decode or measure that footage. A digest mismatch or symlink
holds with `recording_digest_mismatch`. Real tagged recordings require the full
measured import. Provenance is the recorder's evidence assertion, not
cryptographic authentication; synthetic images cannot honestly be labelled measured.
