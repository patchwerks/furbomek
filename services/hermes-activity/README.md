# Hermes public activity module

This module projects real Hermes lifecycle/tool events into bounded public text
and timeline data for the Godot consumer. Hermes remains the only planner. It
does not expose model tools, raw results, credentials, robot or OBS authority.

## Locked runtime

From this directory:

```sh
uv sync --frozen
uv run --frozen python broker.py SPOOL PROFILE_HOME OUT_DIR
uv run --frozen python broker.py SPOOL PROFILE_HOME OUT_DIR --once
```

The uppercase paths are operator-selected arguments. The normal spool is
`/dev/shm/furbomek-hermes-UID/events.jsonl`; output is the media session's private
Kinect directory. The supervisor supplies both explicitly. Cursor/privacy state
and publication sequence are checkpointed with the output. Complete records are
consumed once; partial lines, rotation, truncation and missing history are handled
without relabelling old events as new activity.

`activity.json` uses `furbomek.character.v1`, UTC ISO8601 millisecond timestamps,
increasing publication sequences and bounded TTL. It is a reduced public
projection, not an implementation of the complete future character/A2UI bus.

An explicit `--character-session OPAQUE_ID` enables a bounded local-authorized
character input on the same spool and broker. It is off by default and is not
enabled by the media supervisor. Read [CHARACTER.md](CHARACTER.md) for its strict
input, private-file authorization, cancellation/checkpoint semantics and offline
qualification limits. It does not establish real Hermes or speech integration.

## Privacy and observer contract

The standard-library-only plugin is under `plugin/furbomek_stream/`. Install only
that package into the intended Hermes profile through the host's managed plugin
path. The hooks return `None`, do not start a desktop, do not approve/rewrite tools,
and use nonblocking writer locking. Unavailable observation is not permission to
invent activity or modify agent behavior. Hermes may itself fail closed on a
faulting policy-hook callback; this plugin does not request that authority.

Projection does not publish typed text, literal alphanumeric keypresses, command
contents, file contents, raw tool results or private URL details. Source event
logs and all media remain local/owner-only and outside Git.

**Desktop screenshots are not qualified.** `--screen-policy off` is the supported
default. `--screen-policy bot-desktop` deliberately exits2 before capture. Under
the current observer-only plan, a failed pre-tool observation cannot authorize
uninspected pixels, and the adapter may not acquire tool-blocking authority to
make that guarantee. Screen helpers/privacy fixtures are candidate test surfaces,
not a live-publication capability or a workaround. Do not bypass the CLI refusal.

## Verification

```sh
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen basedpyright
uv lock --check
```

`bash tools/verify-media.sh` from repository root also runs the actual Godot
consumer fixtures and the locked supervisor checks. Real Hermes/OBS acceptance
is separately recorded in `docs/operations/media-integration-2026-10-19.md`.

### Pillow compatibility, 2026-10-30

The dependency is updated from 12.3.0 to 13.0.0 for [issue #13](https://github.com/patchwerks/furbomek/issues/13).
Upstream identifies 13.0.0 as the fix for the
[JPEG thumbnail decoder overflow](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782)
(affected through 12.3.0) and the
[JPEG comment/ICC encoder overflow](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g7cr-3p24-7wf7)
(9.4.0–12.3.0). These advisories do not establish exploitability here: production
code does not load arbitrary image files or preserve supplied ICC metadata.
The capture helper uses ImageGrab, RGB conversion, thumbnail resizing and JPEG
encoding; live capture remains blocked by the CLI.

The [13.0.0 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
remove Python 3.10 support and several unused APIs. This module targets Python
3.12 and does not use those removed APIs. Its conversion to RGB precedes resizing,
so the changed RGBA/LA resize optimization is not used. The lock was regenerated
with the existing uv 0.11.7, preserving lock revision 3 and every non-Pillow package
record, including pytest. No runtime source or capture policy changed.

Observed offline on macOS ARM64/Python 3.12.14: the original 60 tests passed on
12.3.0; adding six synthetic-image cases yielded 66 passes on both versions.
The new cases cover RGB/RGBA/grayscale conversion, aspect-ratio bounds, no upscaling,
full decoding of generated JPEGs, byte-limit equality, quality fallback and
oversize rejection. Those original cases never called ImageGrab or capture_frame; the existing
capture-denial fixture and CLI rejection tests remain in force. Locked lint,
format, types and lock checks also passed. Test execution used an empty
environment with network, private-home/device reads and source writes denied;
dependency preparation used wheels only, without source builds.

Review follow-up replaces the duplicated conversion/thumbnail test operations
with the actual `capture_frame` path. An explicit synthetic fixture replaces
only `ImageGrab.grab` after the suite's capture-denial guard is installed; it
returns a generated in-memory image. The test checks returned dimensions,
decoded JPEG pixels and unchanged source mode, dimensions and bytes. No desktop
capture is performed, and the CLI rejection remains unchanged. The original
results above describe the earlier test revision. The revised suite passed all
66 cases in 4.05 seconds in a separately prepared combined Pillow 13.0.0 /
pytest 9.1.1 environment; this is cross-update compatibility evidence, not a run
against this branch's own frozen lock. Ruff check/format passed and basedpyright
reported zero errors, warnings or notes with that environment's interpreter.
A separate run against this branch's unchanged frozen lock (Pillow 13.0.0,
pytest 8.4.2, Python 3.12.16) passed all 66 tests in 5.66 seconds, Ruff check/format,
basedpyright (zero errors/warnings/notes), and offline lock validation.
All execution used the restricted offline runner. In disposable source copies,
removing thumbnail resizing failed both oversized-image cases; removing RGB
conversion failed all three cases (source mutation, unsupported RGBA encoding,
and grayscale output). The capture-denial fixture remained byte-identical.

This is API compatibility evidence, not an exploit reproduction, Linux/OBS
qualification, desktop-privacy acceptance or confirmation that GitHub alerts have
closed. Those require their respective later checks. Rollback reverts this pin
and lock together, restoring the old advisory exposure; it does not enable capture.


## Opt-in bounded Hermes lifecycle

`--hermes-session OPAQUE_ID` binds one bounded Hermes run to a fresh private
output directory and an already-created empty private spool. It is mutually
exclusive with character mode and requires screen policy `off`. Both paths
must be canonical absolute paths; the spool and its immediate real directory
must be current-UID owned with no group/other permissions. Admission rechecks
file identity and permissions each poll, rejecting symlinks, special files,
rotation and truncation. This is local UID authorization, not protection from
another process using the same UID.

A fresh positive nonfuture selected-session start admits activity. Producer
observations expire at 90 seconds: thinking, tool activity and approval become
`UNKNOWN / Activity unavailable`, without a heartbeat extending their life.
Active public snapshot TTL is capped by the remaining producer freshness window,
so heartbeats cannot advertise another five seconds at its boundary. A consumer
using an inclusive expiry comparison may retain the snapshot for the single
boundary millisecond; no Godot behavior is changed here.
Fresh observations may recover expiry; observation loss, invalid records,
unsafe sources and clock reversal instead persist an irreversible failure
fence. Completion ends the observed step, not the run. An observed session end
is `Session ended` (IDLE), `Session failed` (ERROR), or `Session interrupted`
(INTERRUPTED), using only Boolean metadata, with a permanent tombstone even if
delivered late.
Neither end, failure nor expiry releases unfinished privacy holds.

An immutable private `activity.hermes.binding.json` marker records session, path
and source device/inode. Its presence requires the original flag and a complete
matching checkpoint; marker-only crashes and lost/stripped proof are refused.
Recovery uses a new output directory and source session ID, never deletion of
the marker. Deletion of every proof by a hostile same-UID process is not detectable.

Checkpoint version 3 stores the complete private binding and lifecycle fences
before public publication. Keep its session flag and exact spool on restart;
reuse requires a new output directory and run. Older unbound checkpoints remain
supported by legacy mode but cannot be adopted into a bound run. Private session,
call and path identities never enter the public projection.

The observer records only Boolean `failed`/`interrupted` end metadata, ignoring
raw reasons. Installed Hermes emits this hook per conversation run; it is not
proof of process shutdown, and abrupt termination may deliver no end hook.
This implementation does not qualify live Hermes, Godot, credentials, capture,
speech, hardware or deployment. Offline fixtures are separate evidence.
