# Godot Kinect broadcast viewer

## Scope

This directory is a native Godot 4.7 broadcast viewer. It consumes owner-only files from `FURBOMEK_KINECT_DIR` (default `/dev/shm/furbomek-kinect2-1000`) and must not start, stop, or reconfigure capture, tracking, OBS, networking, or desktop services.

## Snapshot contract

`color_surface.gd` / `.gdshader` render live high-resolution optical pixels as
fine visual samples. They are not an increased-resolution depth sensor. Keep
the on-air `COLOR SAMPLES / DEPTH-PROBED` distinction and preserve native XYZ
modes. A mode toggle must never revive an expired cached color texture or cloud.
Use `probe_optical` for the measured probe's position in this optical view; never
invent an optical coordinate when the calibrated mapping is unavailable.
`optical_box=null` is a real supported state. Hide color-mode ROI overlays and
camera crops, rather than substituting a full image. Retain valid measured XYZ.
The processed magnifier uses native optical pixels near the calibrated probe in
color mode and the registered source ROI in measured mode; keep DESIGN.md and
any on-air/source descriptions consistent with that distinction.

Accept a snapshot only when `tracking.json` has `schema=furbomek.vision.v1`, a fresh `produced_unix_ms` and bounded `ttl_ms`, safe ring basenames, and matching sequence numbers in the cloud's 16-byte header plus both four-byte JPEG wrappers. Reject a mixed or rotating ring snapshot; never combine a cloud from one sequence with images or tracks from another. Expiry hides the cloud and all derived HUD imagery.

## Public activity consumer

All four payload strings `title`, `summary`, `status` and `tool` are required;
`title`, `status`, and `tool` must be nonempty while `summary` may be empty.
Incomplete payloads are invalid, never completed with invented `ACTIVE` defaults.
When testing rejection in an encoded recording, hold the invalid state for at
least three seconds (several polls and encoder buffering), then inspect the
actual program frame for `IDLE` and an absent preview. Do not infer video time
solely from a desktop PNG creation timestamp.

`activity.json` is optional and local read-only. Its event must have `schemaVersion=furbomek.character.v1`, `kind=agent.activity`, source `hermes-adapter`, `a2ui-adapter`, or `glimpse-adapter`, and both `audience` and `sensitivity` set to `public`. Use `seq`, UTC ISO8601 `observedAt`, `ttlMs` (at most 30000), and a `payload` object containing short `title`, `summary`, `status`, `tool`, and optional `image_filename` (same-directory PNG basename). The image is actually rendered in the side window; its PNG dimensions are bounded before decoding. Reject URLs, paths, scripts, unknown sources, stale input, over-64KiB JSON, oversized text, and oversized images. Missing or invalid data is `AWAITING PUBLIC ACTIVITY`, never simulated agent work. This is the project-owned public presentation projection for future A2UI/Glimpse producers, not a claim that a Hermes adapter or the A2UI protocol engine is already deployed.

The canonical producer emits UTC ISO8601 with three fractional-millisecond
digits and `Z`. For shipped v1 compatibility, the consumer also accepts UTC
seconds or one to nine fractional digits, normalizing to milliseconds; integer
or local-time substitutes are invalid. Event `seq` is non-negative and strictly
increases for each accepted publication, including a heartbeat. The producer
persists its sequence across broker restarts; the viewer never invents an
epoch/reset fallback and retains its greatest accepted value for its process.
A rejection, absent file, stale screen,
shutter, or offline state clears decoded preview and screen caches. Privacy
release requires a later screen sequence and a newly decoded image, never an old
texture.

### Frozen v2 Hermes screen projection

The v2 additions are optional. An event with neither addition retains the v1
activity behavior; the renderer never invents a screen, timeline entry, status,
or tool. If present, `payload.timeline` is an array of at most six objects, each
with integer `age_s` in `0..86400`, string `category` at most 12 characters,
string `action` at most 48, string `detail` at most 60, and `status` exactly
`ok`, `error`, or `running`. Reject the whole event when any timeline item is
malformed or out of bounds.

If present, `payload.screen` is an object with `state` exactly `live`,
`shuttered`, or `offline`; `filename` exactly `hermes-screen-0.jpg` or
`hermes-screen-1.jpg`; non-negative integer `seq`; `width` in `1..1280`;
`height` in `1..800`; and integer Unix-millisecond `captured_at_ms`. The filename
is a fixed same-directory basename, never a path or URL. For a live screen, read
at most 2 MiB, decode only with `Image.load_jpg_from_buffer`, and require the
decoded dimensions to match the declared width and height. A bad live JPEG
rejects the whole event. Show it only while `now - captured_at_ms <= 2000`; an
older live frame is `SCREEN STALE` with no image. `shuttered` always clears any
prior frame and renders `PRIVACY SHUTTER`; `offline` renders `SCREEN OFFLINE`.
Reload a JPEG only when its screen `seq` changes.

`activity_fixture_runner.gd` writes only synthetic 4x4 PNG and 8x6 JPEG media to
a private temporary directory, then asserts the reader's public payload and
texture-state contract under `--headless`. Its pass is fixture evidence only; it
does not establish live Hermes, camera, OBS, or visual-reference acceptance.

Poll the activity file at about 125 ms so a broker can present four frames per
second. Cache unchanged JSON text and screen sequence so unchanged content is not
reparsed or decoded every tick. Render all validated public status strings, with
the producer's known states color-coded as: `ACTING` hot crimson; `THINKING` and
`AWAITING APPROVAL` amber without blinking; `PRIVACY SHUTTER` and `ERROR` muted
red; and `IDLE` muted. The broker's known tools are `BROWSER`, `COMPUTER`, `WEB`,
`TERMINAL`, `FILES`, `AGENT`, and `—`; render other validated strings without
inventing a substitution.
