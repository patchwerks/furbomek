# Private media-session supervisor

Owns one capture/tracker/activity/Godot/OBS session. It holds the existing
`host-session.lock`, checks post-start producer freshness, configures the owned
OBS item before OBS startup, and records typed health rather than inferring
physical or recording success from a process existing.

## Runtime and control

The managed user unit launches the locked project:

```sh
uv run --frozen python supervisor.py --settings RUNTIME_SETTINGS_JSON
```

For the installed Brodex unit, agents use:

```sh
bash tools/kinect2/stream.sh start
bash tools/kinect2/stream.sh start --record
bash tools/kinect2/stream.sh status
bash tools/kinect2/stream.sh stop
```

`restart` preserves unspecified runtime settings. `--readiness-timeout-s` accepts
1..300. Settings are atomically written owner-only under
`$XDG_RUNTIME_DIR/furbomek-stream/settings.json` and consumed by the unit's
`--settings` argument. `status` is successful only for an active service with
fresh READY health. `record_requested` is a request, not a claim of OBS recording.
No public streaming flag or destination is created. Existing private `Kinect2`
profile/collection and operator-entered destination settings are preserved.

Screen policy is off. Requests for bot-desktop screenshot publication fail before
worker or desktop startup; see the activity module's privacy qualification gate.

## Lifecycle

Clean viewer/OBS exit ends the whole session. Crashes use per-worker bounded
restart windows/backoff; stale inputs mark health degraded. Children have owned
process groups, bounded TERM/KILL escalation and reaping. Requested recording is
stopped through the owned OBS window's configured F10 hotkey before generic
process cleanup; the callback looks for a fresh recording-stop marker, not an
old log entry or a guessed duration. Private acceptance must still decode the
actual resulting file. The unit uses parent-first `KillMode=mixed` with a bounded
last-resort cgroup timeout so it does not kill OBS before supervisor cleanup.

This deployment does not newly enable login startup. Systemd's process-active state
is not application readiness. A failed sensor, profile, lock or readiness check
must not be hidden by fake activity, automatic firmware reset or extra camera owners.

## Verification

```sh
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen basedpyright
uv lock --check
```

Offline fixtures exercise real child processes without camera, desktop or OBS.
Use root `tools/verify-media.sh` for the combined non-live gate. Deployment,
private recording and rollback evidence are recorded separately; tests alone do
not establish live media acceptance.
