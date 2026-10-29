# Character foundation validation — 2026-10-30

This record covers the bounded local character foundation for
[issue #2](https://github.com/patchwerks/furbomek/issues/2), based on
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. The implementation and this record
are included in the same scoped commit. Read [CHARACTER.md](CHARACTER.md) for
the contract and remaining integration limits. The record date uses Asia/Bangkok.

## Completed local checks

The coordinating agent ran the following checks on macOS in an isolated offline
worker with no credentials, network access or device access. Dependencies were
installed from the existing lock using verified workspace-only uv 0.13.6 and
Python 3.12.16. Candidate execution did not access live Hermes, OBS, media
services or hardware.

| Check | Result |
| --- | --- |
| Complete service pytest suite, with the actual Godot consumer enabled | 121 passed |
| Ruff | Clean |
| Ruff format check | 26 files already formatted |
| basedpyright using the locked environment interpreter | 0 errors, 0 warnings |
| Frozen lock consistency check | Passed; 23 packages |
| Git whitespace/diff check | Passed |

The suite includes real private spool → broker → checkpoint → public JSON
coverage, existing legacy activity behavior, cancellation and replay rejection,
expiry, malformed and discontinuous input, checkpoint authority, restart,
disable/re-enable and bounded rotation reads.

## Actual Godot consumer fixture

The official Godot 4.7 macOS artifact was digest-verified and run headless inside
the same offline boundary. The fixture fed actual broker snapshots into the
existing `ActivityPorts` Control. All six cases and reconnect convergence passed.
These are measured state-application times from that run:

| Broker snapshot | Application time, microseconds |
| --- | ---: |
| Idle | 573 |
| Thinking | 491 |
| Speaking | 419 |
| Interrupted | 368 |
| Error | 459 |
| Exhausted session error | 387 |

These timings measure fixture file write through Control state application.
They exclude broker/consumer poll waits, rendered pixels, display scanout and
OBS. They do **not** qualify event-to-visible latency or real speech timing.
The fixture did not start the viewer's camera scene or change its appearance.

The existing `activity_fixture_runner.gd` passed Godot's check-only validation.
Its local runtime attempt was blocked because its macOS system temporary path
lay outside the worker's allowed temporary directory. The hosted workflow is
configured to execute that baseline fixture on Linux; a hosted result is still
pending and is not included in the local pass count above.

## Remaining acceptance gates

- The full repository `tools/verify-media.sh` gate remains pending.
- The issue #2 event-to-visible latency requirement remains unqualified.
- Formal independent review and acceptance remain pending. Subagent inspection
  found and helped address defects but is not a separate-identity acceptance.
- Real Hermes lifecycle, shared PCM/cancellation integration, OBS, private soak
  and deployment remain separate dependent work. No live producer, robot,
  physical audibility, public broadcast or hardware behavior was tested.

## Rendered demonstration and full media gate follow-up

**Observed and measured, 2026-10-30 (Asia/Bangkok):** the fixture runner in
[`tools/character-demo`](../../tools/character-demo/README.md) exercised the actual
broker and the shipped Godot Control with a real OpenGL renderer. Xeno is the
creator; Furbomek is the character/robot represented by this fixture.

The unchanged broadcast layout was captured at 1920x1080. Its status panel
occupies a narrow left column, so the demonstration now defaults to an enlarged
preview of that same panel in a 1280x720 window. `--full-canvas` retains the native
layout. The production Control and broadcast composition were not modified.

Frames were read back only from the fixture's own viewport after
`RenderingServer.frame_post_draw`; no desktop, camera or OBS capture was used.
Actual PNG text was checked with OCR and rendered frames were visually inspected.
Producer arrivals varied relative to the 120ms broker and 125ms consumer polls.

| Input | Native layout, first matching captured pixels | Enlarged preview, first matching captured pixels |
| --- | ---: | ---: |
| Idle | 63 ms | 47 ms |
| Thinking | 224 ms | 218 ms |
| Speaking | 111 ms | 160 ms |
| Interrupted | 173 ms | 171 ms |
| Error | 116 ms | 160 ms |

All measured transitions were below one second in these two local fixture runs.
During the additional cancelled-speaking replay interval, every captured frame
remained interrupted. That is a rejection observation, not a new-state latency
measurement. The timestamps bound producer-to-rendered-frame capture, including
polling/readback and approximately 100ms sampling; they exclude physical display
scanout, OBS output and audio. This is not a general latency SLA or production
host qualification. The exported video preserves captured timing, with no audio.
Raw PNGs, timestamps, hashes and the video remain local artifacts outside Git.

The full, unchanged `tools/verify-media.sh` gate passed on hosted Linux for
`a8c01317fa739c29cec90060edf92056974b01b0`:
[run 40929646695](https://github.com/patchwerks/furbomek/actions/runs/40929646695/job/123644364679).
It passed 121 gateway tests, 121 activity tests, 18 supervisor tests and 3 camera
snapshot tests (263 total), each module's lint/format/types/lock checks, shell
syntax and the existing Godot activity fixtures. The renderer fixture also
passed parser validation. A dedicated unprivileged worker used isolated
mount/PID/network namespaces, synthetic PTYs and loopback only. Local build
backends ran after isolation; build-only requirements were hash-pinned.

This supersedes the earlier pending full-media-gate and pixels-only evidence
limitations above. Formal independent acceptance remains pending, including
review of the measured rendered-frame boundary against issue #2. Nothing was
merged, installed on the production host, flashed, moved or publicly streamed.
