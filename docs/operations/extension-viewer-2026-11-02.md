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

The proxy is original abstract gray ellipsoid geometry with exactly six static
legs. Curious tilts the head; acknowledge pitches and lifts the whole model.
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

## Evidence and remaining gates

**Observed source inspection only:** the viewer source and manifest boundary were
reviewed without executing candidate JavaScript, installers, hooks or builds on
the credentialed host. Runtime/browser/visual qualification is pending isolated
hosted evidence. No screenshot, build, typecheck, browser acceptance, performance
measurement or accessibility audit is claimed by this record. Intended coverage
includes actual WebGL2, reduced motion, end/reset, stale import races, malformed
and oversized packs, hidden/unmount lifecycle, external resource rejection and
context loss. The dedicated verification owner maintains the exact test/workflow
commands. Update this record only with observed run links and exact revisions.

Review and publishing remain with the coordinator; independent accepted review,
PR 41 dependency disposition and exact candidate qualification are still required.
No deployment, install, activation, claim release, issue closure or live-system
change follows from these source files.

## Rollback

Before integration, discard this isolated viewer candidate. After acceptance,
revert the app, viewer-specific tests/workflow and this documentation together.
It has no installed service, persistent user data, device write or migration.
Do not revert the separately reviewed data-only package or unrelated live state.
