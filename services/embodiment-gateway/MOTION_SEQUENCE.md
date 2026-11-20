---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-07
author: Codex
status: active
---

# Local bounded sequence comparison

Task 11 implements an **offline PTY comparison**, with physical release **HOLD**.
`MotionSequence` is disabled by default. It allocates its own PTY; the supplied
GuardSettings device path is never opened. There is no CLI, model tool, physical
device factory, JSON release permit, or deployed sequence endpoint.

Trusted local code supplies `OfflineQualification` and `SequenceObserver` to
compare exact selected profiles and transitions. A `SequenceRequest` contains
only up to eight steps and a duration of at most 30 seconds. The single queue
rejects competitors. Each step reruns [stage admission](src/furbomek_gateway/stage_admission.py)
against local monotonic time, current pose, stage and stopping envelope, then
calls the unchanged Guard action runner. Forward retains two phases under its
existing action lease; every completed step verifies normal DISARM before the
next step. No shared-ARM or continuous sequence was introduced.

STOP bypasses admission, cancels remaining steps and latches the sequence closed.
Timeouts, stale observations, missing/ambiguous ACKs and uncertain optical
outcomes stop the queue without mutation retry. Results retain per-step Guard
and optical verdicts. A wire completion never asserts physical motion or motor
state. The optical callback is a local observation interface; fixture verdicts
are synthetic and establish no camera or physical acceptance.

Task 14 must preserve production HOLD. A future physical path needs trusted
locally verified qualification, fresh authenticated installed-link evidence from
Task 7, exact measured transitions and stage acceptance, plus the approved user
safety acceptance. Neither `StageReceipt`, replay data nor an `enabled` field
can satisfy these gates. Cower, shake, retreat and blended turns have no qualified
sequence here; use the independently admitted media-only reaction fallback.

Verification: `tests/test_motion_sequence.py` uses an owned PTY, the normal
GuardService/PoweredActionRunner, and a controlled local clock. No hardware,
firmware, camera, OBS, external provider, deployment or physical cadence trial
is part of this comparison. The original Guard lease behavior is unchanged.
