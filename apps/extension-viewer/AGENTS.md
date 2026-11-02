---
created: 2026-11-02T04:52:37Z
branch: codex/32-browser-viewer
author: patchWERKS / Codex
status: active
---
# Local presentation viewer

Read the accepted root and coordination policy; this candidate guide does not
change those authorities. This app is an independent Nuxt root. Never mount the
legacy root app, provider modules, microphone/audio, Hermes, broker, OBS or device
interfaces. Root manifests remain dependency authority for Nuxt/Vue/Bootstrap;
the nested manifest adds only exact-pinned Three.js.

- Import the unchanged browser-only extension-preview core by relative path.
  Use branded parse results directly (shallow refs); do not proxy or clone them.
- Local JSON only, both metadata size and bounded MAX+1 byte read checked. Clear
  prior playback before reading. Keep nonce/unmount guards against stale reads.
- Original gray procedural six-leg geometry only. No imported asset, rig, gait,
  physics, textures, URLs or loaders. Retain provenance and Three MIT notice.
- Initial/reset/end state is paused, position zero, neutral. Render only on
  playback or explicit state/size/preference changes. Reduced motion suppresses
  transforms but retains clock/state. Hide pauses; teardown disposes resources.
- WebGL2 failure/context loss must be explicit, remove the old canvas and disable
  play. Never substitute a canned fallback image and call it rendering.
- Candidate builds, tests and browser execution belong in a credential-free,
  disposable environment. Source inspection on the publishing host is not QA.
