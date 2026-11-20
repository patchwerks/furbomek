---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-07
author: Codex
status: active
---
# Guard acceptance evidence

Task 7 / [physical gate #9](https://github.com/patchwerks/furbomek/issues/9)
adds an offline evidence surface, not a new robot transport. Existing supported
operator-present actions and their historical acceptance remain unchanged.

Run from the repository root:

```sh
uv run --frozen --project services/embodiment-gateway python \
  -m furbomek_gateway.guard_acceptance --replay fixture.json \
  --expected-sha256 REVIEWED_FIXTURE_SHA256
```

The strict `ReplayFixture` schema in `guard_replay.py` describes abstract inputs.
The expected digest must come from the reviewed fixture, separately from the
bytes being assessed. The CLI binds those bytes and compares actual outcomes
against the fixture expectations. Exit 0 means only replay PASS; exit 2 means
HOLD. Missing, altered, malformed and misleading success inputs fail closed.

The probe uses a deliberately public HMAC fixture key, not a production secret
or a proposed installed wire protocol. It tests expected origin, integrity,
boot/session, next sequence and a bounded expiry against independently supplied
fixture context. Lost ACK, reset and cancellation latch against further mutation.
STOP is unconditional and does not clear that latch. This abstract probe is not
an emulator, HIL, native firmware authentication, power measurement or evidence
that the current Guard understands signed commands. Existing native and PTY
suites independently cover the actual current protocol and cancellation path.

`GuardAcceptance` emits separate `replay`, `installed`, `supervised` and
`unattended` verdicts, input digest, outcomes, reasons and
`physical_motion_authorized=false`. This implementation can only emit HOLD for
all three physical scopes. `--run-approved FILE` always exits 2 without reading
that purported approval or opening any device. It cannot be used as a live
probe launcher. No JSON flag, fixture signature, host authentication or sequence
number substitutes for robot-side qualification.

A future separately authorized installed qualification must bind exact robot
and bridge image hashes and transport identity to independent instrumentation,
physical admission, fresh robot-side origin/integrity/session rejection tests,
all STOP/loss routes, reset/brownout behavior and measured rail cutoff. It must
preserve the 500 ms RF lease, 3 s operation and 30 s session bounds unless a
separate versioned qualification authorizes changes. Neither historical bench
receipts nor this offline result opens that gate. Unattended release remains
HOLD until the installed path and independent cutoff are actually qualified.
