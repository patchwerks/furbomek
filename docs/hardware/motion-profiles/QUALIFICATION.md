---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-02-task-02
author: Codex
status: active
---
# Portable motion qualification rubric v1

**Proposed physical qualification; observed software contract only.** No measured
profile, current stage, installed firmware change or motion authorization is
created by this specification. Existing supported-bench limits remain in force.
The [current roadmap](../../../PLAN.md#93-phuket-motion-qualification-for-streaming)
and [uncalibrated camera evidence](../../operations/macos-table-walk-and-media-2026-11-20.md#overhead-camera-and-motion-scoring)
remain the starting point. This rubric must be fixed before collecting comparison
trials; any tighter criterion needs a dated rationale before those trials.

## Portable records

The gateway `motion_contracts` module exports version-1 `MotionProfile`,
`ObservationCalibration`, `StageProfile`, and `TrialEvidence`. Parse external JSON
with `model_validate_json`; never use Pydantic's unchecked `model_construct` or
`model_copy(update=...)` at the input boundary. Unknown fields/versions, nonfinite
numbers, reversed intervals and invalid polygons are rejected. Coordinates use
millimeters and degrees, body X forward, Y left, yaw positive counterclockwise.
The finite numeric domain is limited to absolute values at most 1e9 to avoid
arithmetic overflow. Polygons are strictly convex, counterclockwise, without a
repeated closing vertex. Concave usable areas require future subdivision; they
must not be silently replaced by a bounding rectangle.

`profile_id` is a computed SHA-256 of the versioned body model excluding its
historical evidence collection list. It binds robot revision, installed-image
hash, gait revision, verb, start/end posture, power regime, load class, tested
surface intervals and envelope bounds. It excludes stage IDs, dimensions and
camera pose. JSON persistence retains all historical `TrialEvidence`, including
collection calibration ID, sample count, provenance class and artifact digest.
Consumers recompute `profile_id` after loading. Synthetic and recorded-replay
provenance are not powered evidence. Adding evidence without changing the model
does not change the model ID; changing bounds does.

Each stage has its own anchored frame, survey digest, usable polygon, explicit
hazard list, containment evidence digest and referenced profile and calibration.
Calibration coverage is expressed in that anchored **stage frame**. Its
`observation_to_stage` is a rigid planar transform: rotate observation coordinates
counterclockwise then translate. It is applied after camera calibration has
produced metric planar coordinates, not directly to image pixels.

`motion_admission.assess_stage(AdmissionContext)` checks record consistency,
coverage, freshness, pose visibility, surface interval compatibility and unresolved
hazards. A different observation revision, expired calibration, mismatched stage
binding or uncovered vertex produces a serialized `hold` with reasons. Validity
is `[valid_from_ms, valid_until_ms)` on one caller-supplied epoch millisecond clock.
The caller must update observation revision on camera movement, changed optics,
crop, target identity or any other invalidating observation condition. IDs and
digests are references, not authentication or proof that a referenced file exists.

An `eligible` receipt only permits proceeding to further admission checks.
`physical_motion_authorized` is always false. Task 9 owns measured-profile reuse,
position-dependent clearance, containment inspection and final stage policy; the
runtime must still enforce robot identity, fresh observation and physical gates
at dispatch. No DTO constructor or simulation enables motors.

## Measurement protocol and hold criteria

1. Survey the usable region and hazards independently. Calibration targets must
   cover the complete operating region, including feet and all boundaries.
   Validate with independent known translation along both planar axes and known
   yaw, using held-out targets/trials. Record residuals and uncertainty separately
   and use their conservative combined bound for the contract error fields.
   Initial limits are at most 5 mm and 2 degrees; observed error must also be
   strictly below one quarter of the smallest admitted move on **each scored
   axis**. Use the minimum across translation axes in the version-1 scalar field.
   Inability to measure a posture or meet a limit means unmeasurable/HOLD; never
   zero travel, success or inferred safety. Changed view requires revalidation.
2. Measure every verb separately: Active, Sleep, forward, backward, left, right,
   turn-left and turn-right. Check expected signed displacement, settle time,
   start/end posture and complete phase sequence. Newly authored poses, sequences
   and transitions require their own evidence. No locomotion qualification follows
   from an ACK, DISARM, or a posture-only test.
3. Bind the installed image hash and robot/gait revisions; record actuator supply
   regime, representative battery range and loading. A surface class includes
   material and finish IDs and measured slope/static-traction intervals expanded
   by measurement uncertainty. Use a repeatable coupon matching foot material and
   representative loading; retain method, instrument, repetitions and raw samples
   in the private digest-addressed trial artifact. Reuse requires material/finish
   equality and new measured intervals contained in tested ranges. Otherwise hold
   affected verbs for targeted retest; do not discard applicable historical data.
4. For every pose and axis, retain swept footprint, observed maximum stopping
   distance, worst travel during the admitted observation/watchdog interval and
   uncertainty. Clearance is their sum. Version 1 supplies a conservative radial
   envelope containing every measured pose/axis; `clearance_mm` sums those four
   bounds. Use one common trial sample count and explicit assumption IDs for all
   bounds; retain per-axis distributions/counts in the referenced artifact. An
   axis with inadequate evidence cannot be hidden by a larger aggregate count.
5. Require independently measured actuator cutoff with monotonic timestamps,
   authenticated/fresh robot traffic, priority local STOP and the applicable loss
   matrix before powered qualification. Camera frame timing is not cutoff timing.
   Firmware reset, retry or uncertain movement never automatically clears a hold.
   Task 7 owns physical safety evidence; task 9 owns placement/clearance decisions.

Raw geometry, recordings, addresses and calibration artifacts remain private.
Repository fixtures are explicitly synthetic; reviewed public summaries contain
run IDs and digests only. A future release must verify the referenced artifacts,
qualification provenance and live prerequisites rather than trust supplied IDs.
