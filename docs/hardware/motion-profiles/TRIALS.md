---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-05
author: Codex
status: active
---
# Whole-set trial catalog v1

**Observed software replay only. Physical qualification remains HOLD.**
[Catalog status](catalog-v1.json) records zero accepted physical trials and no
invented metric values. Historical supported-bench actions and the uncalibrated
two-phase forward recording remain historical; neither is converted into a
calibrated profile. No hardware, firmware, installed image, or runtime has changed.

The offline executable accepts a [closed trial manifest](trial-manifest-v1.schema.json)
and emits a [catalog receipt](catalog-receipt-v1.schema.json). Run from the repository:

```sh
uv run --frozen --project tools/motion-lab python tools/motion-lab/trials.py \
  --replay docs/hardware/motion-profiles/replay-empty-v1.json
uv run --frozen --project tools/motion-lab pytest tools/motion-lab/tests/test_trials.py
```

The shipped manifest is explicitly synthetic and empty: expected exit 2/HOLD.
Tests project independent synthetic camera corners for all eight verbs, ten trials
per verb. A full replay fixture can be generated without hardware:

```sh
PYTHONPATH=tools/motion-lab uv run --frozen --project tools/motion-lab python -c \
  'from tests.trials_fixture import catalog; print(catalog().model_dump_json())' \
  > /tmp/furbomek-synthetic-trials.json
uv run --frozen --project tools/motion-lab python tools/motion-lab/trials.py \
  --replay /tmp/furbomek-synthetic-trials.json
```

Exit 0 means `REPLAY_COMPLETE`, with supervised and unattended statuses still
HOLD. `--run-approved PATH` always exits 2 before reading that path or a replay
manifest. There is no physical transport adapter in this tool. Actual calibrated
stage, independently measured cutoff, and authorized physical acceptance remain
missing prerequisites; this work cannot close the physical portion of Task 8.

## API and evidence

`trials.replay_catalog(TrialManifest, directory)` recalculates every nested
`ScoreInput` using `score.score_run`; supplied score summaries cannot authorize
or count a trial. Every attempt remains in `trials`, with reasons, optical result,
protocol outcome, and SHA-256 of its canonical trial JSON. Keep that JSON and
referenced recordings privately to resolve the evidence digest. Artifact digests
in stage/cutoff/clearance fields are references, not proof of their existence or
physical qualification. They do not bypass the physical HOLD.

`ProfileOutcome` separates portable `candidate` and computed `profile_id` from
collection stage data. Candidates reuse the gateway's `MotionProfile`,
`TrialEvidence`, `StageProfile`, and `SurfaceClass` contracts. A fixed repository
path in `trials_gateway.py` imports only DTO/geometry modules, never hardware
adapters; no manifest field controls imports. Canonical DTO source is the sibling
`services/embodiment-gateway/src/furbomek_gateway` tree in the same checkout.
Synthetic candidates retain synthetic provenance; measured recordings become
`recorded_replay`, never physically qualified `measured` evidence.

Each declared verb/start/end pose/surface/load/power combination needs ten valid
attempts. Any rejected attempt holds its entire profile for investigation. Six
locomotion verbs need three recovered headings separated by at least 30 degrees
and observations in each of at least two disjoint voltage bands. A single-band
exception requires an explicit limited-range evidence reference and retains that
range in the portable candidate assumptions; physical verification remains HOLD.
Missing exposed start poses must be declared as additional profiles before replay.
This evaluator cannot discover undeclared mechanical poses.

Active requires signed upward height, Sleep downward height; the other six verbs
require their exact signed body axis. Mixed, wrong, partial, unsettled, missing,
repeated-exposure or no-travel evidence never counts. Normal DISARM is independently
required after guarded completion. Static traction/material/finish/slope must be
within declared surface bounds; post-stop drift holds. Unmeasurable slip is not a
claim of zero slip or a substitute for independent traction measurements.

Clearance checks use the exact supplied convex stage polygon and start point,
subtracting conservative footprint, peak excursion, stopping excursion, interval
travel and uncertainty. No stage geometry is manufactured from a historical
recording. Portable body coordinates are forward X, left Y, CCW yaw, millimeters
and degrees. Height and settle-time distributions remain in per-trial scorer
metrics; candidate planar envelopes do not erase those observations. Task 9 may
consume these candidates for replay comparisons but must retain all physical
HOLDs and separately validate stage, cutoff, provenance, and real trial evidence.
