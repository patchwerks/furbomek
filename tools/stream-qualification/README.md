---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-10-task-27
author: patchWERKS / Codex
status: active
---
# Offline streaming qualification

This is Task 27's offline evidence gate for Task 17 in the approved motion/effects
plan. It implements the numerical checks and a bounded admission-policy replay.
It does **not** run the gateway, sequencer, OBS, providers, camera, robot, or HIL.
It does not certify the installed system or change any operational state.
See [the project roadmap](../../PLAN.md#93-phuket-motion-qualification-for-streaming)
for the separate physical release requirements.

## Runnable surface

From the repository root, with Python 3.11 or later:

```sh
python3 tools/stream-qualification/run.py --suite replay
python3 tools/stream-qualification/run.py --suite replay --manifest /private/evidence/candidate.json
python3 tools/stream-qualification/run.py --suite release-check --manifest /private/evidence/candidate.json
python3 tools/stream-qualification/run.py --suite approved-live --manifest /private/evidence/candidate.json
python3 -m unittest discover -s tools/stream-qualification/tests -v
ruff check tools/stream-qualification
```

The runner and tests use only the standard library: no ambient Pydantic, NumPy,
pytest or provider packages. The explicit standard-Python task requirement takes
precedence over the general programming skill's preferred library choices.
`replay` exits 0 only for successful offline metric/matrix validation; all failures
exit 2. `release-check` and `approved-live` always exit 2 with named release HOLDs.
Argument syntax errors also exit 2. A zero replay exit code is never release approval.

`approved-live` refuses before opening the supplied manifest. `release-check`
reads only the explicitly supplied bounded regular JSON file to diagnose candidate
consistency; it never opens paths contained in its contents. Symlinks, special
files, duplicate JSON keys, nonfinite numbers, unknown fields and coercible types
are rejected. Inputs are capped at 4 MB and arrays at 100,000 entries. An input is
not an authority source even if its path names a production manifest.

## Input and receipt contract

[models.py](models.py) defines immutable types; [parsing.py](parsing.py) owns the
strict boundary. [fixtures/representative.json](fixtures/representative.json) is
an entirely synthetic example, with a zero source revision and dummy hashes.
No installed version or device identity is encoded in the fixture.

The top-level fields are exactly `schema_version` (1), `scope`, `timings`,
`faults`, and `evidence`. No `pass`, `approved`, trust flag or operational endpoint
is accepted. Scope contains a full lowercase 40-digit source revision; 64-digit
SHA-256 robot image, bridge image, profile, stage, calibration and motion-envelope
identities; and a bounded session identifier. Scope equality includes every field.
These values are candidate claims, never independently observed installed state.

Timings use one named monotonic clock domain and nonnegative integer nanoseconds.
Frames contain `at_ns`, cumulative `rendered` (total render opportunities, including
lagged frames), and cumulative `lagged`. Adjacent samples must increase, span no
more than 60 seconds, and report 30 fps within two frame opportunities. Resets,
counter regressions and missing sampling intervals hold. The validator subtracts
the first counter values from the last; it does not trust supplied aggregates.
The rehearsal must span at least 1,800 seconds at 1920×1080/30, with lag ≤2%.
This proves arithmetic on inputs, not that footage is representative.

`cues`, `motion`, `provider`, `camera` and `encoder` contain raw `received_ns`,
`completed_ns`, `idle` samples. Receipts report counts and nearest-rank p95:
`sorted_latencies[ceil(0.95 * count) - 1]`. Local cue p95 must be ≤250 ms; motion
p95 is ≤500 ms for idle samples only. Non-idle samples are counted separately.
All samples must lie within the frame window, be individually ordered and have
strictly increasing receive times. Empty series hold. Provider, camera and
encoder distributions are separately reported and never subtracted from the
local cue or dispatch calculation. A real instrumenter must capture each boundary
on the correct clock; this runner cannot establish clock provenance.

Each fault case names a `Fault` enum value and ordered `{at_ns, action}` events.
Actions are qualify, trigger, dispatch, loss and recover. Every required fault
must appear exactly once. The admission-policy model drops pending commands and
qualification on loss; recovery alone cannot resume motion, and qualification
alone cannot restore the old trigger. The trace must exercise refusal after
recovery and a new qualified trigger. Owner override retains its own fallback.
Every reported dispatch is **simulated**; none is sent to an adapter. The matrix
covers OBS, missing stage, tracking stale/bump/disconnect, RF, Mac, tunnel,
Brodex restart, reset/brownout, near-boundary, cancel/STOP, renderer stall, owner
override, provider outage/reconnect, backlog, battery service, independent cutoff,
resource contention and early loss. These fault labels do not prove native fault
injection or real stop behavior; Task 17 must repeat the actual integrated cases.

Candidate evidence envelopes contain exactly `kind`, full `scope`,
`captured_unix_ms`, `expires_unix_ms`, `payload` and `payload_sha256`.
The digest is SHA-256 of the exact UTF-8 payload string. Each expected kind must
appear once: authenticated link, independent cutoff, stage, containment, matched
live scope, private 24-hour soak and operator authorization. Payloads are opaque
local evidence bytes: hashing them checks integrity only. Their contents cannot
assert authenticity or satisfy a physical gate. Scope must match and current
wall time must lie in a validity window no longer than 24 hours. Session mismatch
rejects a previous authorization receipt. A matching window is not sufficient
proof of freshness on a real route.

Output includes `schema_version`, `suite`, individual SHA-256 values for the six
runner modules (`run.py`, `models.py`, `parsing.py`, `metrics.py`, `faults.py`,
`qualification.py`) and a digest of that map serialized as sorted-key compact JSON, and, when read, the exact input-byte
SHA-256 and candidate scope. It reports computed metrics, per-fault replay counts,
candidate-envelope consistency holds, `release: HOLD`,
`physical_authorization: false`, and `operational_io: false`. Replay evidence
checks are diagnostic: missing physical receipts do not make a valid synthetic
replay fail. They always prevent release.

## Task 17 handoff

There is intentionally no installed trust-root backend in this lane. No manifest
can remove the named holds for installed authenticated link, independent cutoff,
instrumented stage/containment, current operator authority, matched live scope,
representative private 24-hour soak or absent live execution integration.
Do not add an `--allow`, receipt PASS bit or environment override to bypass them.

The independently authorized Task 17 operator must first verify the actual Task 7
installed authenticated route and measured physical cutoff, exact source/image/
profile/calibration/stage/envelope bindings, current session/authority, contained
stage, native fault injection and representative battery service/resume behavior.
That work must capture native timing/frame evidence for a 30-minute rehearsal and
24-hour private soak, correlate decoded program and independent pose/stop evidence,
and measure zero unexpected actuation, stale resume or boundary loss. Task 16's
integrated reaction rehearsal remains a separate prerequisite. Resource holds and
battery service invalidate admission; elapsed time never overrides them.

A future independently reviewed integration must consume trusted installed and
instrumented evidence through an explicitly qualified verifier before extending
this CLI. The current `approved-live` spelling is a safe refusal surface, not an
operator instruction or implemented rehearsal runner. Keep raw media, private
receipts, keys and live identifiers outside Git. This offline result requires no
rollback of hardware or host configuration because neither was changed.
