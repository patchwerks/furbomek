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
`view.js` exposes only the pure `FurbomekView.createView(...)` factory, which
binds a new adapter to text-only DOM updates. `boot.js` owns the ordinary page's
instance privately; `fixture.js` owns its separate opt-in instance in a closure.
No live adapter is published as `window.FurbomekAvatar`. The pure factories carry
no current renderer state and provide no transport or privileged capability.
Classic scripts preserve ordinary `file://` loading without a server, module-CORS
overrides or a generated bundle.

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
maximum 8192 bytes and existing text-field limits counted as Unicode code points,
matching the Python producer rather than JavaScript UTF-16 code units. Invalid, expired, future, duplicate
and older sequence inputs cannot update state or extend TTL. Any observed backward wall-clock shift clears the current caption immediately,
including before TTL expiry. Inputs remain rejected until wall time reaches its
previous high-water mark. The last accepted sequence is retained; old state never
resurrects when time catches up. A new, fresh, higher-sequence projection is required
to restore presence. Strictly newer full snapshots
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

The ten-minute private OBS/CEF acceptance is blocked pending access to Brodex
from Xeno. Do not start that live test until access and the exclusive operator window
are available. Before accepting #5, the designated media operator must obtain an
exclusive private OBS window, preserve existing scenes/settings/destinations,
load the local fallback as a separate Browser Source, and record ten minutes of
actual full-frame output.
Verify alpha/capture behavior, startup/shutdown, hide/show, source refresh, missing
asset, fixture-label permanence and expiry on that exact OBS/CEF build. Hash and
fully decode the private recording; keep raw media outside Git. Record health,
resource ownership and restoration of prior scene/settings. Do not imply the
future renderer-failure switch is implemented: Stream Director comes later.

To stop the local preparation, close the local page. Repository rollback must
remove or revert this directory together with the new avatar-only
[fixture workflow](../../.github/workflows/avatar-fallback.yml), keeping its source
paths and checks consistent. Existing launch commands, service configurations,
media destinations, root packages and shared contracts are unchanged. Future OBS
acceptance must remove only its owned source/scene and restore the saved
configuration. Do not close #5 or claim its ten-minute gate from these offline results.

## Review corrections, 2026-10-30 (Asia/Bangkok)

Independent review found UTF-16 length mismatch and pre-expiry clock rollback.
Three added regressions reproduced both defects before correction. The adapter
now uses codepoint counts and the fail-closed clock policy above. All 11 boundary
tests and the real-browser fixture check passed after correction in the restricted
QA worker. Private OBS acceptance and Stream Director integration remain pending.

A further malformed-input review found that an object timestamp could throw during
regular-expression coercion. The adapter now requires a string timestamp before
parsing it. A regression covers object, number, null and array timestamps through
both input methods, preserving accepted state and its original expiry. All 12 Node
boundary tests passed in the restricted offline worker. This correction adds no
browser or OBS acceptance evidence.


## Private view-instance correction — 2026-10-30

The normal page no longer exports its live adapter. The browser regression now
observes rendered DOM state and checks that `window.FurbomekAvatar` is absent on
the default, demonstration and hostile-text pages. The separate test-only
`tests/hostile.html` uses the same view factory and a literal hostile-caption
fixture; it is never loaded by the normal page. Thinking, interruption-label,
expiry, fixture provenance and text-only rendering checks remain covered.

Observed: all **15 Node tests** passed in the existing credential-free worker
with network, device/private-home reads and source writes denied. The three new
view tests execute the actual classic scripts with synthetic DOM/timers and
cover private-instance absence, honest offline startup, single fixture startup,
interruption/expiry, pagehide timer cleanup and missing-asset shutdown. They do
not establish browser/CEF behavior. The separate Linux CI run below now qualifies this correction's real-browser
fixtures; earlier browser evidence above remains historical. No OBS, provider,
transport or device was started for this correction.

## Automated browser fixture check

[The avatar workflow](../../.github/workflows/avatar-fallback.yml) runs for pull
requests targeting `main` and pushes to `main` that change this directory or the
workflow; manual dispatch is also available. It pins the official Playwright
`v1.64.1-noble` image at
`sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea`
and both `playwright` and `playwright-core` packages at 1.64.1 with explicit
SHA-512 tarball checks in the workflow. Preparation downloads and verifies those
inputs without running candidate code. Node tests and the actual Chromium
`file://` fixture check then run as an unprivileged user in a read-only,
network-none, resource-bounded container with dropped capabilities, no privilege
regain and an empty inherited environment. Only this public static-fixture source
and the verified browser libraries are mounted; no runner home, credentials,
Docker socket or host device mount is supplied.

Playwright defaults Chromium's inner sandbox to off. The mandatory outer
container restrictions provide this job's execution boundary; the test must not
be copied into an unrestricted credential-bearing runner. Browser success checks
these local fixtures and the absence of a global live adapter, not OBS CEF,
private recording, a live broker or Stream Director acceptance. Because the
workflow and assertions are editable in a pull request, its result is advisory
and requires review of the exact revision; it is not independent trust approval.
**Observed Linux evidence:** [run 41027253714](https://github.com/patchwerks/furbomek/actions/runs/41027253714)
at `14e42629ab9d6abd3d1ba26f18d8004daaebbba1` passed all 15 Node tests and the
actual Chromium browser check (offline asset, explicit fixture, interruption,
expiry, literal hostile text, absent live global and no page errors). The
container boundary assertions also passed. This is browser-fixture evidence
only; private OBS recording and CEF qualification remain outstanding.

## Documentation closeout — 2026-10-30

Corrected the repository rollback to include the added avatar fixture workflow and
aligned the [scoped agent guide](AGENTS.md) with that reviewed CI scope. The private
ten-minute OBS/CEF gate remains blocked pending access to Brodex from Xeno. This update
changes documentation only and adds no runtime, browser or live acceptance evidence.
