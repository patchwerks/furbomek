# Dirty stream work: relevance and disposition

Date: 2026-10-18. Assessment against `da76188` and the current dirty main checkout.

## Decision

**Relevant, unfinished implementation. Not obsolete, not superseded, and not
ready to adopt as a completed feature. Keep it as the starting point for the
existing Hermes/activity/supervision milestone; do not discard it or rebuild the
same components from scratch.** This assessment is not a request to implement
that entire milestone or activate its services.

The source is in `/home/lock/dev/patchwerks/furbomek`, branch `main`:

| Dirty work | Current purpose | Disposition |
|---|---|---|
| `services/hermes-activity/` | Hermes hook projection, private event spool, broker state and public activity/screen producer | Retain; directly addresses PLAN §9.1 adapter/broker work; fix integration blockers before adoption |
| `services/stream-supervisor/` | Candidate worker supervision for capture/tracker/broker/Godot/OBS | Retain as unfinished lifecycle implementation; not a replacement for the documented launcher yet |
| `tools/kinect2/stream.sh` | CLI for the candidate user service | Retain with supervisor; record-option propagation is incomplete |
| `tools/kinect2/godot/activity_event_reader.gd` and modified `activity_ports.gd` | Optional screen/timeline validation, freshness and rendering | Retain together; the modified renderer preloads the new reader, so deleting just the untracked file breaks that source dependency |
| Modified Godot `AGENTS.md`, `DESIGN.md`, `broadcast_hud.gd` | Contract/layout documentation and relocation of the offline annunciator around the new left column | Retain with the same UI slice, not stale robot-control work |

No tracked equivalent of the new broker, supervisor or reader was found in the
current tree or existing local branch history. The committed public activity
consumer does not replace the missing producer. PLAN §9.1 still calls for a real
redacted Hermes run through a broker and whole-stack lifecycle supervision.

## Concrete adoption blockers

1. `services/hermes-activity/broker.py` defines `run()` but has no executable
   entrypoint or argument parser. The supervisor launches it as a script with
   spool/profile/output arguments; that invocation simply exits without running
   the broker. A safe execution with nonexistent fixture paths returned normally
   without starting the loop or accessing any device.
2. Broker `ActivityEvent.observed_at` is an integer serialized as `observedAt`;
   Godot `_observed_msec()` accepts only a UTC ISO8601 string. Its current emitted
   events therefore fail the actual consumer contract despite passing unit tests.
3. Broker `run()` rereads the complete spool every iteration and reapplies all
   events. It needs incremental consumption/deduplication and rotation tests to
   avoid replayed timeline/state and falsely refreshed activity.
4. `hermes_feed.spool_directory()` returns a directory while the plugin's default
   spool is its `events.jsonl` file. That helper is currently unused; the supervisor
   explicitly passes the file. Unify the defaults when implementing the entrypoint,
   rather than presenting the unused helper as a working default launch path.
5. The supervisor lacks the working launcher's readiness/OBS-configuration and
   explicit duplicate-camera locking behavior. Restart-window enforcement and
   descendant cleanup require tests before it owns the live media stack.
6. `stream.sh start --record` parses the flag but does not pass it to the service
   or supervisor. It cannot truthfully promise recording through that option.
7. The observer's pre-tool hook can start `bot-desktop`; review this side effect
   against the observer-only boundary before adopting the plugin. Screen capture,
   privacy behavior and actual Hermes hook wiring remain unqualified here.

**Host wiring is present, not missing:** read-only `systemctl --user show` found
`furbomek-stream.service` loaded but inactive, with its fragment at
`~/.config/systemd/user/furbomek-stream.service`. Its ExecStart points to the dirty
`services/stream-supervisor/supervisor.py`. No unit is tracked in this project.
This makes the prototype operationally relevant, not evidence that it works.
Do not infer the unit is absent merely from a repository search, or start it to
test relevance. No service state was changed in this assessment.

## Validation actually performed

From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python /usr/bin/python3.12 --with 'pytest>=8,<9' --with 'pydantic>=2,<3' --with 'pillow>=12,<13' pytest -q -p no:cacheprovider services/hermes-activity/tests
bash -n tools/kinect2/stream.sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --python /usr/bin/python3.12 services/stream-supervisor/supervisor.py --help
systemctl --user show furbomek-stream.service -p LoadState -p ActiveState -p FragmentPath -p ExecStart -p WorkingDirectory
```

Observed **21 tests passed**, shell syntax passed, supervisor help printed, and
service was loaded/inactive. These tests cover projection/broker units, not the
producer-to-Godot or full supervision integration. Source inspection and safe
script execution established the missing broker entrypoint. No camera, OBS,
desktop capture, public streaming, robot or live Hermes session was started.
No source file in the assessed dirty work was edited, discarded or published.

## Next implementation boundary

Continue this coherent slice: broker entrypoint and file-consumption contract,
producer/consumer fixture regression, then supervisor parity/cleanup/record flag
tests, then separately authorized private live acceptance. Do not mark PLAN §9.1
complete from the existing 21 unit tests. Preserve source and tests; generated
Python/pytest/Ruff caches are not source and must be excluded from publication.
The unknown original author is not a blocker to this relevance decision.
