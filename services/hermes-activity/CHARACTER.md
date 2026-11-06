# Local character foundation

This opt-in input extends the existing activity broker for
[issue #2](https://github.com/patchwerks/furbomek/issues/2). It supplies ordered
character presentation through the existing read-only Godot activity port. It
does not connect a real Hermes lifecycle or jabberWERK speech, implement a PCM
clock, start media, or grant robot/OBS/tool authority. Those integrations retain
their own issue dependencies and acceptance gates in [PLAN](../../PLAN.md).

## One broker, explicit local authority

The existing broker accepts `--character-session OPAQUE_ID` in addition to its
existing positional arguments. The flag is absent by default. No extra listener,
queue service or worker is created. The existing media supervisor is unchanged
and does not activate this feature.

Character rows use the existing JSONL spool, with these additional admission
requirements:

- the opened descriptor and current path must identify the same regular file;
- the file and its immediate parent must belong to the broker's current UID;
- the parent must be a directory and both it and the file must have no group or
  other permission bits; file/parent symlinks are rejected;
- the row's strict nested session must match the explicitly selected session;
- its sequence, timestamp, TTL, phase and utterance/cancellation identity must
  validate before reduction.

The output directory must also be a real current-UID private directory, and any
existing checkpoint must be a current-UID private regular file, not a symlink.
Checkpoint replacement uses mode 0600 and does not follow a pending-file symlink.
Checkpoint reads use no-follow descriptors, validate ownership and regular-file
status before reading bounded JSON, and reject incomplete persisted character
fields. These protections also apply to already-bound state when projection is
disabled and are rechecked before consuming subsequent input. Legacy checkpoints
without character state may retain read-only group/other bits, as may legacy
output directories; checkpoint files are rewritten mode 0600 without changing
directory permissions. Group/other write access is always rejected. Once a
character session is bound, both directory and checkpoint require private modes.
This compatibility exception is implemented by [`persistence.load_checkpoint`](persistence.py)
(reject group/other writes) and [`runtime._require_private_character_state`](runtime.py)
(require private modes). A legacy activity-only checkpoint contains activity
recovery state; a bound checkpoint also carries durable character session and
cancellation evidence. Removing read-only legacy bits automatically would change
existing output-directory access, while accepting them for bound state would
weaken its private-file boundary. The exception therefore ends at session binding
and does not authorize group/other writes or relax character input admission.
Create the private spool before activating character mode; missing input is a
continuity failure, not permission to start with invented history.

This is **local-authorized** input, not multi-user authentication. The identifier
is not a password. Processes sharing the authorized UID can write this spool;
untrusted producers therefore require a distinct execution identity and a
separately qualified adapter before deployment. Renderer processes receive only
the public snapshot and must not receive write access to the spool/checkpoint.
Permissions are checked without changing them or repairing an insecure source.

## Input contract

A complete newline-terminated spool row remains bounded to 4096 bytes. Existing
observer records remain unchanged. A character row uses the existing wrapper
with `kind: "character"` and a strict nested `character` object:

```json
{
  "v": 1,
  "kind": "character",
  "ts_ms": 1700000000000,
  "session": "fixture-session",
  "action": "presentation",
  "detail": "",
  "character": {
    "schema_version": "furbomek.character-input.v1",
    "session": "fixture-session",
    "seq": 0,
    "observed_ms": 1700000000000,
    "ttl_ms": 1000,
    "phase": "speaking",
    "utterance": "fixture-utterance"
  }
}
```

The timestamp above is a historical schema example, not runnable fresh input.
The wrapper's text is not projected, and its privacy fields cannot release the
existing screen shutter. Only the nested object controls character reduction.
Unknown nested fields are rejected, including attempts to add commands or URLs.

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `furbomek.character-input.v1` |
| `session` | Explicit broker session; ASCII alphanumeric first character, then alphanumeric, dot, underscore or hyphen; at most 64 characters |
| `seq` | Strict integer from 0 through 2^53−1; accepted values increase within the configured session |
| `observed_ms` | Positive Unix milliseconds from the local producer; freshness only, never an audio clock |
| `ttl_ms` | Strict integer 1–30000; accepted only while `observed_ms <= now < observed_ms + ttl_ms` |
| `phase` | `idle`, `thinking`, `speaking`, `interrupted` or `error` |
| `utterance` | Required only for `speaking`, using the same bounded identifier syntax |
| `cancel_of` | Required only for `interrupted`; names the utterance being cancelled |

For ordinary state updates the state machine rejects duplicates, older sequences,
decreasing producer timestamps, future/expired input and mismatched sessions.
Cancellation is deliberately more conservative: an authorized, session-matching,
nonfuture cancellation retains its target's tombstone even after its presentation
TTL or when delivered out of order. Its sequence watermark never decreases and
an expired/out-of-order interrupted visual is never replayed. A cancelled, replaced,
completed or expired utterance is retired and cannot become speaking again with
a larger sequence. Repeated cancellation is idempotent. Cancelling utterance A
while replacement B is speaking retains B and records A's retirement. Returning
to idle/thinking/error retires the previous active utterance.

The broker keeps at most 128 retired identities per session. Reaching capacity
fails closed in error rather than evicting old cancellation evidence. This is a
bounded foundation, not a long-running voice session qualification. A future
producer contract may replace this bound only with independently tested replay
and generation semantics.

## Snapshot, restart and compatibility

Character state, sequence and retirement evidence live in the **existing atomic
activity checkpoint**, alongside its spool cursor and publication sequence.
Checkpoint version 2 reads the previous version 1 format; no dependency or public
activity schema version changes. Version 1 checkpoints contain no character
state; activating this slice requires a fresh private output directory when
previous publication exists, because historical cancellation cannot be proven.

Disabling the flag hides the character projection but continues processing valid
input for an already bound session privately, preserving new cancellations as
well as prior sequence and retirement evidence. Re-enabling the same session
resumes that evidence. A different session cannot replace an existing session in the same
output directory. A new session requires a new unique identity and a fresh
private output directory; never rotate identities to retry cancelled work.
Missing, invalid or character-less historical evidence fails closed whenever
either a checkpoint or a published activity file already exists, until
a new session/output directory is deliberately selected. Do not delete an active
checkpoint, reuse a prior session identity or downgrade an active session to an
older broker: those actions discard the evidence needed to reject replay.

Malformed input or lost spool continuity retires active speech and exhausts the
character session. Recovery requires a deliberately new session/output directory;
the broker cannot prove which cancellation records were lost. Polling is
bounded to 64 KiB from the current generation and, when switching a fully drained
rotation, at most another 64 KiB. It does not allocate an unbounded input queue.
An old rotated file is drained before legacy cursor migration; character rows
from a descriptor that no longer matches the current source path are rejected.
This conservative failure does not silently replay transient state.

The public `activity.json` remains `furbomek.character.v1` / `agent.activity`,
consumed by the existing activity port. It contains fixed status/title/summary
text and the existing redacted timeline, never producer identifiers, arbitrary
character text, credentials or input payloads. Its existing `hermes-adapter`
source names the adapter surface; fixture character states do not establish real
Hermes activity. Publication happens in the same poll when character state
changes. Its TTL never exceeds the remaining character-input lifetime, so a
broker failure cannot renew a speaking label indefinitely.
Exhausted error is a durable current status, so its public heartbeat uses the
standard bounded five-second TTL rather than the expired input lifetime.

## Verification and evidence limits

The existing locked tests, Ruff, formatting, basedpyright and lock checks apply.
New tests exercise the real spool → broker → checkpoint → public JSON path,
private-file admission, cancellation, expiry, malformed input, restart,
disable/re-enable, session replacement rejection and bounded rotation reads.

`tests/test_character_consumer.py` additionally uses an explicitly supplied
`FURBOMEK_GODOT` executable to feed those actual broker snapshots into the existing
Godot `ActivityPorts` Control and to check reconnect convergence. Without that
executable the test reports a skip, not a consumer pass. The fixture prints
consumer state-application time in microseconds. That measurement excludes poll
wait, rendering, display scanout and OBS; **it is not event-to-visible latency**.
The fixture does not launch the viewer's camera scene or any media service.

This foundation alone does not close #2. Visible-state timing below one second,
the full non-live media gate and independent acceptance remain necessary. It
does not satisfy #6 real Hermes lifecycle, #7 shared PCM/OBS speech, or #8 private
soak. No live producer, physical audibility, hardware, deployment or public
broadcast qualification is implied.


The separate `--hermes-session` mode projects one bounded Hermes lifecycle and
is mutually exclusive with `--character-session`. It ignores nested character
presentation rows and retains its own version-3 private lifecycle authority.
Neither mode adds speech, pixel capture, planning or actuation capability.
