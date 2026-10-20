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
