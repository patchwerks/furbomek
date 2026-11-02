---
created: 2026-11-02T04:52:37Z
branch: codex/32-browser-viewer
author: patchWERKS / Codex
status: active
---
# Local presentation viewer candidate

Scope: [issue 32](https://github.com/patchwerks/furbomek/issues/32), building on
PR 41 head `8c38c3fd814cc7dfdfd25ee706e5718f28f0de28`. The accepted policy base
remains main `cdd9147fac9141fa0c75b5058f9dce46c7885188`; the package PR remains
under review. The user authorized this bounded original procedural proxy viewer
while review is pending. Implementation does not constitute acceptance or closure.

## Implemented source boundary

`apps/extension-viewer/` is its own Nuxt application with its own `app.vue` and
config. It imports Bootstrap CSS and existing root Nuxt/Vue tooling; its nested
manifest/lock adds only exact-pinned `three@0.187.0`. The [root manifest](../../package.json) and [root lock](../../package-lock.json)
remain the authority for shared Nuxt/Vue/Bootstrap dependencies. Root dependency files and
`packages/extension-preview/` remain unchanged. It never mounts the legacy root
app or its providers and never requests microphone, audio, camera, media, speech,
Hermes, broker, OBS, robot or network-resource-loader capabilities.

The unchanged `parsePack` and `samplePack` browser entry consume a bundled
four-second fixture or one explicitly selected local JSON file. Import clears
old playback immediately, checks `File.size`, reads only `slice(0, MAX+1)`, checks
the resulting bytes, and uses the strict core parser. A nonce invalidates older
reads on another selection, example restore, and unmount. Filename and errors use
Vue text interpolation. Invalid input cannot preserve an old animated pack.

Playback starts paused and neutral at zero. Play/pause/reset, deterministic
millisecond seeking, expression/reaction text, and event seek controls are local.
Reaching the end resets to paused neutral zero; manually seeking to duration
shows the core's neutral endpoint. A hidden document pauses, and an unmounted
view cancels animation, invalidates imports, disconnects the resize observer,
removes listeners and disposes GPU geometry/materials/renderer/context. There is
no idle animation loop. Reduced motion suppresses all character transforms while
the time/state display remains usable.

WebGL2 absence or context loss produces an explicit error, disables Play, resets
state, disposes resources and removes the old canvas. No canned visual substitutes
for a failed renderer. CSP confines resources to this origin, disables objects,
forms and media, and permits inline styles/scripts needed by Nuxt's generated
entry. This is a presentation boundary, not a hostile-browser sandbox.

## Geometry and design provenance

The proxy is original abstract gray ellipsoid and cylinder geometry with exactly
six connected static two-segment legs and overlapping endpoint joints and feet.
Curious tilts the head; acknowledge pitches and lifts the whole model.
There is no gait, rig, physics, measured geometry, source photograph or imported
model. The page explicitly labels Procedural proxy, Presentation preview, and
No physical simulation. Existing project assets remain excluded pending rights.

Source bytes, SHA-256, provenance and dependency notice source are retained in
[`proxy-provenance.json`](../../apps/extension-viewer/proxy-provenance.json).
Three's full [upstream MIT notice](https://raw.githubusercontent.com/mrdoob/three.js/7e89746a687bb88271253698fa108b1dd59825d0/LICENSE)
at source commit `7e89746a687bb88271253698fa108b1dd59825d0` is retained and linked
from the app footer; copyright is © 2010-2026 three.js authors.
Photo Atlas was consulted before asset selection; no functional asset fit this
local viewer. No reference photograph was copied or generated.

The Taste skills informed hierarchy, spacing, typography, contrast and restrained
motion. This is a contributor workbench rather than a marketing page: Bootstrap
controls, system fonts, roughly 65/35 stage/inspector, neutral auto light/dark theme,
one blue accent, variance 3 / motion 2 / density 5. Mobile collapses to one column.

## Observed hosted evidence and remaining gates

[Advisory qualification run 41393178172](https://github.com/patchwerks/furbomek/actions/runs/41393178172)
completed successfully for source `782bee3f12eff3872bf5b72dc46ebabe6ae823f4`,
against accepted enforcement `cdd9147fac9141fa0c75b5058f9dce46c7885188`.
The unchanged core dependency is PR 41 head
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28`. Evidence records the actual candidate
SHA separately from the workflow's merge-ref artifact name.

Both Node **22.22.3** and **26.7.0** jobs passed locked installation with lifecycle
scripts disabled, Nuxt prepare, Vue typecheck and static generation. Each passed
**62/62 tests** (59 core and 3 viewer artifact checks), with zero failures,
cancellations, skips or todos. Both typecheck logs were empty. Each matrix job
also passed **23 browser cases** using Playwright **1.64.1**, Chromium on Linux
and SwiftShader software WebGL2. Both browser result files recorded empty
outbound-request and page-error arrays. Browser cases cover import rejection and
races, playback/seeking/reset/end, real rendered cues, reduced motion, hidden and
unmount lifecycle, WebGL failure/context loss, dark link contrast and deterministic
first-frame clock ordering. The latter guards the runtime defect observed in
[run 41392296078](https://github.com/patchwerks/furbomek/actions/runs/41392296078).

The exact meaningful commands in the
[qualification workflow](../../.github/workflows/extension-viewer.yml), run from
the isolated source root, are:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm ci --prefix apps/extension-viewer --ignore-scripts --no-audit --no-fund
./node_modules/.bin/nuxt prepare apps/extension-viewer
./node_modules/.bin/vue-tsc --noEmit -p apps/extension-viewer/tsconfig.json
./node_modules/.bin/nuxt generate apps/extension-viewer
VIEWER_SOURCE_ROOT=/source/apps/extension-viewer node --experimental-vm-modules --test packages/extension-preview/tests/*.test.mjs apps/extension-viewer/tests/*.test.mjs
node apps/extension-viewer/tests/browser-check.cjs
```

The workflow supplies pinned images, timeouts, a restricted dependency proxy,
resource limits, read-only source and temporary scratch storage. Candidate code,
configuration, compilation and tests execute only in separate credential-free,
nonroot disposable workers with no network; browser paths are explicitly supplied.
No candidate installer, hook, build or JavaScript ran on the publishing host.
The commands above document that qualification context, not host execution advice.

Bounded PNG artifacts are `desktop-light.png`, `desktop-dark.png`, `mobile.png`
and `mid-cue.png`. The parent coordinator viewed all four final Node 22 images
and judged the connected six-leg proxy, light/dark layout, mobile layout and
mid-cue presentation acceptable for this bounded preview; the dark links were
readable. Automated checks additionally assert the two dark-link contrast ratios.
This visual review is separate from independent PR acceptance.

This is exact-source advisory evidence, not main integration or repository-wide
lint/CodeQL acceptance. Full browser coverage, hardware GPU/performance testing,
a full accessibility audit, physical behavior, canonical character asset rights
and live-system acceptance remain unqualified. Independent review of
[PR 41](https://github.com/patchwerks/furbomek/pull/41) and
[PR 42](https://github.com/patchwerks/furbomek/pull/42), retargeting to accepted
main and fresh checks remain required. The coordinator retains publishing and
claim ownership. No installation, deployment, activation, claim release or issue
closure is implied by these results.

## Rollback

Before integration, discard this isolated viewer candidate. After acceptance,
revert the app, viewer-specific tests/workflow and this documentation together.
It has no installed service, persistent user data, device write or migration.
Do not revert the separately reviewed data-only package or unrelated live state.
