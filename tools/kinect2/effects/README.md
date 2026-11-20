---
created: 2026-11-20T08:00:00Z
branch: codex/production-wave-03-task-10
author: Codex
status: candidate
---
# Candidate effects consumers

Task 10 / [framing issue 57](https://github.com/patchwerks/furbomek/issues/57).
`inventory.json` distinguishes hardware, inference and presentation. `catalog.json`
lists the four implemented looks and explicitly unavailable capabilities. This is
an offline-tested candidate, not an installed release or a live performance pass.
The previous 16.6% quiet-session rendering lag has no isolated cause or claimed fix.

## Godot mailbox

The main scene instantiates `effects_consumer.gd`. It reads only `effects.json`
beside its existing private camera files and atomically replaces `effects-ack.json`.
`control.schema.json` describes the closed input. Write via a temporary file and
rename. These files need the same owner-only directory boundary as camera frames;
the mailbox grants no network or public-provider authority.

Read the process-generated `consumer_id` and current revision from the ACK first.
Every request includes that consumer ID, the exact current `expected_revision`,
and `revision = expected_revision + 1`. Requests older than 1000 ms, from a prior
process, with an expired duration, or without a fresh source are refused. A lease
uses monotonic expiry after admission. Unknown fields, paths, malformed values,
unsupported looks and out-of-range controls are rejected without changing the
current owner. Revision arbitration is a consistency fence; Task 14 must provide
authenticated owner admission. A receipt is not camera or physical qualification.

Stable looks are `rgb.fixed.v1`, `rgb.crimson.v1`, `xyz.depth.v1` and
`xyz.crimson.v1`. RGB fixed always retains the full optical image. Crimson framing
evaluates ordered `subject`, `fixed`, `hold` rules. `subject` requires the exact
track ID, object/body/face kind, a bounded optical box and a source age within
`ttl_ms` (maximum 600 ms). It never substitutes a depth surface for robot identity.
No matching rule holds the previous crop. `fixed` deliberately returns to full
frame; `hold` deliberately retains the crop. The HUD uses the same locked identity.
Native XYZ uses bounded camera yaw/pitch/zoom; framing rules do not manufacture
3D tracking or fill holes. Controls are immediate except for the smooth sinusoidal
pulse, limited to 1 Hz and 25% overlay alpha. Point size changes sample styling,
not sensor resolution. Custom shading and scene blends are unavailable.

Expiry restores fixed RGB. Local keys, wheel input and the existing `view.json`
override revoke the active lease and advance its revision. An old expiry can no
longer overwrite that operator edit. Source expiry hides geometry, images and
pulse; the existing snapshot reader remains the sequence/freshness authority.

Task 4 mapping for Task 14: `graphics.pulse.v1` presets `neutral` and `rgb` select
`rgb.fixed.v1`; `xyz` selects `xyz.depth.v1`; `liquidation` selects
`rgb.crimson.v1` with `pulse_hz = 1`, forwarding bounded intensity and duration.
Use full-frame framing by default, point size 1.45, zoom 1, yaw/pitch 0, visible HUD
and insets. Obtain consumer identity and revisions locally; never copy them from a
provider. Task 4 schemas are unchanged. HUD redacted cues continue through the
existing character contract; this adapter does not bypass its public-text checks.

## Candidate OBS sound adapter

`obs-effects.lua` is intentionally separate from the installed `obs-edge.lua`.
It requires a pre-provisioned `Furbomek Program SFX` ffmpeg source, visible in
`Kinect Program` within profile and collection `Furbomek Mac Test`. It never
creates sources, selects devices, changes profiles or starts outputs. Installation
requires its own private OBS acceptance; the catalog reports SFX unavailable.
The existing edge adapter's single-source binding rule also needs a reviewed
integration before a two-source scene can be deployed. Do not silently change it.

Generate original half-second mono 48 kHz PCM tones using
`godot --headless --path tools/kinect2/godot --script res://effect_audio_builder.gd -- PRIVATE_ASSET_DIRECTORY`.
The measured file peak is -12.248 dBFS. The adapter additionally caps its source
gain at -12 dB, disables monitoring and starts muted. Only an explicit owner script
setting can unmute. `assets` and `mailbox` are private operator configuration;
requests cannot set paths. Input `sfx.json` and atomic `sfx-ack.json` follow
`sfx.schema.json`, with only `liquidation` and `acknowledge` presets.
Because Lua's wall clock has second precision, `issued_ms` must be a Unix-second
boundary multiplied by 1000. The wire encoding uses flat identifier strings and
decimal integer literals. Expiry uses OBS monotonic time. Source loss, mute and
unload stop the retained owned source. No microphone or monitoring is enabled.

## Offline verification

`godot --headless --path tools/kinect2/godot --script res://effects_fixture_runner.gd`
uses a private synthetic fixture to exercise parsing, mailbox ACK, conflict,
subject identity, stale/lost targets, native holes, overrides and expiry.
`effects_render_runner.gd -- REPLAY_DIRECTORY OUTPUT_DIRECTORY` requires a real
GPU renderer and archived matching cloud/JPEG files with a replay `tracking.json`.
It requests an archived-replay caption. Never reuse tracks from a different
sequence. Its output is actual rendered 1920x1080 images, not a desktop screenshot.
Encode those images privately for decode inspection; this does not measure live
sensor cadence, glass-to-program latency, OBS rendering lag or audio playback.

**Observed capture limitation:** native OpenGL and ANGLE fixture captures, including
the native movie path, intermittently omitted text in some frames. The caption is
therefore not reliable on every standalone frame. Keep these diagnostic artifacts
private and labelled by their manifest; visual acceptance and installed release
remain HOLD. No root cause, performance improvement or deployment fix is claimed.
Use `--audio-driver Dummy` for offline movie capture. Its fixed output frame rate
does not establish real-time cadence or the on-air timing of a wall-clock pulse.

Lua boundary fixtures can run without OBS using a Lua interpreter, or a temporary
`uv run --with lupa==2.8 python` runtime loading
`tools/kinect2/effects/tests/obs_effects_test.lua`. These test parsing and default
mute only; they are not a playback or profile-installation qualification.
