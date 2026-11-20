---
created: 2026-11-20T12:25:00Z
branch: codex/production-wave-06
author: Codex
status: active
---
# Independent stage verification (Task 9)

**Observed software result:** two explicitly synthetic layouts can select the
same Task 8 forward profile through independently recomputed optical calibration.
**HOLD:** no second physical stage, new-stage translation/turn/stop acceptance,
authenticated release permit, or unattended qualification is established here.
No hardware, camera capture, serial, OBS, or host configuration is accessed.

Run from the repository root:

```sh
uv run --frozen --project tools/motion-lab python tools/motion-lab/stage.py \
  --verify tools/motion-lab/fixtures/stage-0.json --at-ms 10000
uv run --frozen --project tools/motion-lab python tools/motion-lab/stage.py \
  --verify tools/motion-lab/fixtures/stage-1.json --at-ms 10000
```

Exit 0 means `REPLAY_ELIGIBLE` only. Exit 2 means `HOLD`, including malformed or
missing evidence. `physical_motion_authorized` is always false; supervised and
unattended status are always HOLD. Clock overrides require synthetic input and
synthetic input requires an explicitly named `replay_comparison`. A measured
import uses the real wall clock and existing hash-checked image importer; even
valid `observation_check` data cannot issue a release permit.

Store real bundles outside Git in an operator-private mode-0700 directory under
opaque stage IDs. The committed fixtures contain invented synthetic geometry,
source digests and surface values; they are not physical containment evidence.
`tests/stage_fixture.py:write_fixtures` regenerates the candidate through Task 8's
actual optical replay scorer, then projects independently surveyed target poses
for two camera distances/orientations. The stage axes rotate and its usable region
grows; the robot-relative profile identity and historical evidence do not change.
The replay covers one selected forward profile, not all eight physical actions.

## Input and consumer contract

[`stage_verification.py`](stage_verification.py) owns `StageBundle`:

- `calibration_input`: existing Task 5 `CalibrationInput` including held-out
  independent survey poses. Measured input must have actual hash-checked images.
- `calibration_receipt`: actual recomputed `CalibrationResult`; its input digest
  hashes the canonical `calibration_input.model_dump_json()` bytes. The Task 2
  calibration's `independent_validation_sha256` hashes this canonical receipt.
- `request`: gateway `stage_models.StageRequest`, with the existing Task 2
  `AdmissionContext`, independent `StageSurvey` and `ContainmentCheck`, fresh
  `CurrentConditions`, explicit selected profile IDs, invalidation and margin.

`verify_bundle(bundle, directory, now_ms)` reruns calibration, compares the exact
receipt, enforces camera/reference/stage identity and error/freshness limits,
checks coverage against the held-out survey hull, and checks observed start pose.
It then calls gateway `stage_admission.verify_stage(request)`. Calling the latter
alone checks declared geometry and conditions; it does not independently run
optical calibration or establish the authenticity of source records.

Survey and containment hashes bind the complete typed records, including survey
revision, polygon, obstacles and surface. Containment must be a distinct source,
match the exact survey and encompass its usable polygon. Hashes detect mismatched
records; hashes and input assertions do not authenticate a physical survey.

Every step requires fresh robot/firmware/gait, power/load/posture and surface
conditions. The current footprint must fit the profile's swept radius. The
conservative clearance disk adds swept radius, stop excursion, inter-observation
travel, motion uncertainty, nominal displacement, calibration translation error
and explicit margin. Every convex stage edge and every obstacle must clear the
whole disk strictly; contact with a boundary holds. This intentionally rejects
some paths that a richer swept-volume calculation could accept.

A camera change invalidates local calibration; arena/survey changes invalidate
local containment. A changed robot, gait, surface, posture, load or footprint
holds the affected selected profile. No operation rewrites prior motion metrics,
installs a permission or copies approval from another stage.

For Tasks 11/14, consume `StageReceipt.request_sha256`, `profile_id`, `stage_id`,
`local_checks_passed`, reasons and required clearance for the exact bounded step.
Re-evaluate against the fresh state for every step. Do not cache a receipt as
physical authority. An independently authenticated local release gate must bind
the exact current request and targeted translation/turn/stop evidence, installed
robot-link authentication, stopping/cutoff evidence and other release conditions.
That gate is external to Task 9; self-attested JSON cannot satisfy it. Keep Task 7
and Task 8 physical HOLD states separate from this replay comparison.

Focused verification:

```sh
uv run --frozen --project services/embodiment-gateway pytest -q \
  services/embodiment-gateway/tests/test_stage_admission.py
uv run --frozen --project tools/motion-lab pytest -q \
  tools/motion-lab/tests/test_stage.py
```
