---
created: 2026-11-19T23:50:00Z
branch: codex/production-wave-03-task-05
author: patchWERKS / Codex
status: active
---
# Motion lab calibration

**Implemented and replay-tested; physical calibration remains HOLD.** This tool
recovers camera intrinsics, lens distortion, fixed-reference extrinsics and a rigid
chassis target's metric pose. It grants no robot motion, stage admission or
clearance qualification. No serial, robot, OBS or network API is present.

The documented camera mode is **Logitech Webcam C930e, 640×480, 15 fps,
YUYV422**, as [observed previously](../../docs/operations/macos-table-walk-and-media-2026-11-20.md#overhead-camera-and-motion-scoring).
The isolated locked project reuses OpenCV 4.11.0.86 / NumPy 1.26.4 from
[the camera snapshot lock](../../services/camera-capture/tests/test_snapshot.py.lock).
Python is restricted to 3.12 for that NumPy wheel family. No installed host Python
or existing tracker environment is changed.

## Printable fixture and measurements

Print [tag-sheet-a4.svg](fixtures/tag-sheet-a4.svg) on A4 at actual size / 100%,
with fit-to-page disabled. The vector geometry is dimensioned, **not a measured
physical print**. Verify black square sides 40 mm ±0.25 mm, both adjacent
reference center baselines 120 mm ±0.25 mm, and the 100 mm ruler before import.
Wrong printed scale holds. Four fixed tags are IDs 0, 1, 2, 3 from OpenCV
`DICT_4X4_50`. Keep their white quiet zones; mount the board flat and immobile.
Cut only below the dashed line and mount ID 10 rigidly and parallel to the
chassis's reference plane. Its black square is also 40 mm. Do not scale or
individually reposition reference tags. A board corner is not a stage boundary.

Board coordinates in mm: ID 0 center `(0,0,0)`, ID 1 `(120,0,0)`, ID 2
`(120,120,0)`, ID 3 `(0,120,0)`. x points right and y down on the printed board;
z points into it. A target raised 65 mm above the board has z = **-65**.
Yaw is about positive z. These are observation coordinates, **not** the gateway's
robot `x_forward_y_left_yaw_ccw` frame. A later stage/robot transform must be
surveyed explicitly. The solver composes full target and reference poses;
it never maps elevated target corners through a floor homography.

The sheet generator is `print_tags.py`. Its vector grid was rendered and all
five tag IDs decoded for QA. Layout: one A4 page, fixed board above the cut line,
separate chassis target below, measurement instructions and ruler visible.

## Independent setup branches

`setup: clearance` requires a rigid camera, fixed board, full independently
labelled near/far/side boundary visibility, **all feet** visible, contact labelled
`contact`, and separately verified physical containment. The camera can retain
its existing height and aim at a smaller fully visible zone. There is no assumed
camera height, table dimension or minimum stage size. A reference board does not
establish containment, and this tool does not qualify the robot's travel envelope.

`setup: rear_diagnostic` preserves `contact_label` (`unknown`, `supported`,
`contact`, `airborne`) and per-frame visibility records in the imported private
manifest, but always returns `rear_diagnostic_clearance_unqualified`. A rear view
can diagnose feet; it cannot admit clearance. No hardware action is part of setup.

Acquire at least eight diverse tilted/rotated board images at the same lens/mode
for intrinsic recovery. Lock focus/zoom and the final camera position, then record
a fixed reference plus at least three independently surveyed target poses spanning
the minimum scored translation and yaw. Reference tags stay fixed in these
validation/current frames. Measure target height at each pose; do not use fitted
positions as validation truth. Synthetic fixtures use an independent analytic
Brown lens projector, two different camera poses, and 65 mm target elevation.

The measured-input JSON has the same closed schema as the
[camera-1 fixture](fixtures/camera-1.json), but `provenance: measured` and **every
frame** must name a same-directory PNG `image_file` and its `image_sha256`.
Raw measured images stay in a mode-0700 private directory outside Git. Import
checks hashes, rejects image symlinks and path traversal, decodes actual ArUco
corners, and ignores supplied marker coordinates. Camera revision, reference
revision, timestamps and contact/visibility labels are operator evidence; do not
invent them. Focus/zoom/resolution changes require a new camera revision and lens
fit. Changing a reference requires a new reference revision and calibration.

## Agent-operated commands

From the repository root:

```sh
uv run --frozen --project tools/motion-lab pytest -q tools/motion-lab/tests/test_calibrate.py
uv run --frozen --project tools/motion-lab python tools/motion-lab/calibrate.py \
  --input tools/motion-lab/fixtures/camera-1.json --at-ms 10000 \
  --output "$P/calibration/replay-camera-1"
uv run --frozen --project tools/motion-lab python tools/motion-lab/calibrate.py \
  --capture --camera 'Logitech Webcam C930e' \
  --input "$P/calibration/import.json" --output "$P/calibration/fresh-capture"
```

Provision `P` outside Git with mode 0700. Outputs must be new directories; existing
or symlink outputs are rejected without overwriting prior receipts. The CLI creates
private files (umask 077), `private-input.json` and `calibration.json`. Capture adds
`current.png` and `capture.log`. It is video-only, one frame, with a 15-second
subprocess timeout. It requires a complete measured import and preliminary fit
before opening the camera. Coordinate exclusive camera ownership first.

A new capture intentionally resets contact/visibility labels to unknown: it holds
until the actual new image is independently inspected, hash-bound and reimported.
Old labels cannot authorize a new image. Missing prerequisites return a typed HOLD
without camera access. `--at-ms` is restricted to synthetic replay; measured
current images must be within 600 ms of the actual evaluation clock. This offline
CLI is preparation/diagnostics, not a continuous runtime observer. Future live
admission needs its own fresh visibility observer and validated stage contract.

Exit 0 means `CALIBRATED_REPLAY` or `CALIBRATED_OBSERVATION`; exit 2 means `HOLD`.
`motion_admitted` is always false. Consumers must check both exit code and typed
status/provenance. Measured inputs cannot be relabelled from simulation to imply
physical evidence. The receipt retains input digest, lens, site extrinsics,
revision bindings and independent error bounds for downstream private analysis.

## Gates and limits

Intrinsics require view diversity and RMS ≤1 px. Markers require all four corners,
a 2 px image border and at least 100 px² area. Fixed-reference drift above 1 px
holds. Independent 3D translation error plus survey uncertainty must be ≤5 mm,
yaw ≤2°, and each strictly below one quarter of the minimum scored movement.
Current target position/height must remain within the independently validated
region plus its measured uncertainty. Missing tags, wrong print dimensions,
cropped boundaries/feet, unknown contact, unverified containment, stale/future
frames, changed camera/reference or excessive residuals hold.

These are bounded calibration checks, not probabilistic confidence, safety-rated
metrology, a watchdog, or general camera-motion detection. Global scene movement
that preserves all image geometry is not observable by monocular tags alone.
The current physical C930e view has no mounted measured tags or independently
verified containment and remains HOLD. Synthetic numerical precision is not a
physical accuracy claim. Lens distortion and target pose use pinned OpenCV
[calibration APIs](https://docs.opencv.org/4.11.0/d9/d0c/group__calib3d.html)
and [ArUco detection](https://docs.opencv.org/4.11.0/d5/dae/tutorial_aruco_detection.html).

Quality gates: `uv run --frozen --project tools/motion-lab ruff check tools/motion-lab`,
`ruff format --check` under that same project, and `basedpyright --project tools/motion-lab`.
The type configuration documents three upstream NumPy/Pydantic/Typer/OpenCV stub
limitations; application contracts remain closed, finite and immutable.
