---
created: 2026-10-29T16:57:52Z
branch: codex/5-avatar-fallback
author: Codex
status: active
---
# Static avatar fallback preparation

Tracks [Furbomek #5](https://github.com/patchwerks/furbomek/issues/5).
This implements the offline static browser renderer portion of [PLAN §6.5](../../PLAN.md).
Private OBS recording, live broker connection and Stream Director integration remain pending.
It neither controls nor starts OBS, Hermes, audio, camera or hardware.

## Local entrypoints

Open `index.html` as a local browser file for the honest offline fallback. It does
not invent activity. `fixture.html` is a separate opt-in demonstration: it shows
“FIXTURE · NOT LIVE”, changes from thinking to interrupted, then expires to offline.
It never loops or labels a fixture as a real Hermes run. Both use the same adapter.
They require no npm install, HTTP server, CDN, network, keys or proprietary runtime.

The transparent scene contains an original abstract six-legged emblem and readable
caption plate. The asset is a schematic fallback mark, not an approved canonical
photorealistic character or an animated rig. `assets/manifest.json` records its exact
version, provenance, SHA-256 and rights limitations. No existing rig or image with
verified redistribution rights was found in the inspected repository assets.

Design: static operational presence, restrained monochrome with one pale-green
accent; variation 3 / motion 1 / density 2. The Taste Skill and local Photo Atlas
catalogue were consulted. No photograph was selected or copied because a transparent
operational emblem fits this slice better. No third-party model, image or font ships.

## Narrow adapter

`adapter.js` exposes `FurbomekStatic.createAdapter({render, now, fixture})`.
`view.js` binds it to text-only DOM updates as `window.FurbomekAvatar`.

| Method | Behavior |
|---|---|
| `capabilities()` | Static SVG, transparency; no expressions, visemes, audio or transport |
| `load_character(id)` | Only `furbomek-static-plate-v1`; no arbitrary paths/URLs |
| `health()` | Failed before load/after shutdown, degraded offline, ready with fresh projection |
| `apply_snapshot(rawJson)` | Consume a fresh public activity envelope; return acceptance boolean |
| `apply_event(rawJson)` | Same full-envelope projection path; not a delta or command dispatcher |
| `set_visible(boolean)` | Local presentation visibility only |
| `snapshot()` | Current bounded presentation state; expires old captions |
| `tick()` | Paint current state; view ticks every 100 ms |
| `shutdown()` | Idempotent terminal hidden/offline state; no service/process control |

Input is the existing `furbomek.character.v1` / `agent.activity` public projection
from `services/hermes-activity/activity_models.py`, not a new character broker.
Only title, summary and status reach the DOM. Screen, filenames, timeline and extra
fields are ignored. The consumer requires `hermes-adapter`, public audience and
sensitivity, safe integer sequence, UTC millisecond timestamp, 1–30000 ms TTL,
maximum 8192 bytes and existing text-field limits. Invalid, expired, future, duplicate
and older sequence inputs cannot update state or extend TTL. Once observed expired,
state cannot return after a wall-clock rollback. Strictly newer full snapshots
converge; sequence reset requires a new adapter instance, not an inferred session.

The fixture uses the same envelope with permanently separate fixture provenance.
It proves display changes, not real Hermes activity. This consumer does not implement
the future broker's session/cancellation/speech semantics. “Interrupted” is just a
public label here; no audio or animation exists to cancel.

There is deliberately no WebSocket, fetch, message listener or credential entrypoint.
CSP disallows connections, inline script, remote images, objects and forms. Text uses
`textContent`, never HTML. A future trusted integration must supply already approved
public projection; the public label alone is not redaction or authentication. Adding
a transport or claiming session replay must be a separately reviewed broker integration.

## Verification

From repository root:

```sh
node --test tools/avatar-fallback/tests/*.test.mjs
```

Optional real-browser check with an already installed Playwright and Chromium:

```sh
FURBOMEK_PLAYWRIGHT=/absolute/path/to/playwright \
FURBOMEK_CHROMIUM=/absolute/path/to/chromium \
node tools/avatar-fallback/tests/browser-check.cjs
```

Set `FURBOMEK_AVATAR_QA_OUTPUT` to an existing private output directory to retain
screenshots. Browser dependencies are test-only, never runtime dependencies. Use a
disposable profile and a credential-free worker with network/device/home restrictions.
The test owns and closes only its spawned browser, not the user's browser session.

Observed on 2026-10-29: 8/8 Node boundary tests passed; real headless Chrome loaded the
local index and fixture, displayed thinking → interrupted → offline, retained the
fixture label, and rendered hostile HTML literally with no page errors. Screenshots
at 1280×720 were visually inspected. Final verification used an empty environment,
temporary HOME, private-home content restrictions and denied TCP/IP network/device
access; browser-local Unix IPC and temporary writes were allowed. This is browser
fixture evidence, not OBS CEF, real broker, audio or private-media qualification.

## Remaining acceptance and rollback

Before accepting #5, the designated media operator must obtain an exclusive private
OBS window, preserve existing scenes/settings/destinations, load the local fallback
as a separate Browser Source, and record ten minutes of actual full-frame output.
Verify alpha/capture behavior, startup/shutdown, hide/show, source refresh, missing
asset, fixture-label permanence and expiry on that exact OBS/CEF build. Hash and
fully decode the private recording; keep raw media outside Git. Record health,
resource ownership and restoration of prior scene/settings. Do not imply the
future renderer-failure switch is implemented: Stream Director comes later.

Rollback for this preparation is closing the local page/removing this directory.
No existing launch command, service configuration, media destination, root package,
workflow or shared contract has changed. Future OBS acceptance must remove only
its owned source/scene and restore the saved configuration. Do not close #5 or claim
its ten-minute gate from these offline results.
