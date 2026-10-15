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
incomplete payloads are invalid, never completed with invented `ACTIVE` defaults.
When testing rejection in an encoded recording, hold the invalid state for at
least three seconds (several polls and encoder buffering), then inspect the
actual program frame for `IDLE` and an absent preview. Do not infer video time
solely from a desktop PNG creation timestamp.

`activity.json` is optional and local read-only. Its event must have `schemaVersion=furbomek.character.v1`, `kind=agent.activity`, source `hermes-adapter`, `a2ui-adapter`, or `glimpse-adapter`, and both `audience` and `sensitivity` set to `public`. Use `seq`, UTC ISO8601 `observedAt`, `ttlMs` (at most 30000), and a `payload` object containing short `title`, `summary`, `status`, `tool`, and optional `image_filename` (same-directory PNG basename). The image is actually rendered in the side window; its PNG dimensions are bounded before decoding. Reject URLs, paths, scripts, unknown sources, stale input, over-64KiB JSON, oversized text, and oversized images. Missing or invalid data is `AWAITING PUBLIC ACTIVITY`, never simulated agent work. This is the project-owned public presentation projection for future A2UI/Glimpse producers, not a claim that a Hermes adapter or the A2UI protocol engine is already deployed.
