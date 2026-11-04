---
created: 2026-11-02T05:52:55Z
branch: codex/32-browser-viewer
author: patchWERKS / Codex
status: active
---
# Issue 32 browser compatibility and keyboard evidence

**Observed bounded qualification:** source
`87a50b335a58dea2b4920a53afd14913de405765` passed 30 browser scenarios in each
of four browser/build combinations in
[run 41408050074](https://github.com/patchwerks/furbomek/actions/runs/41408050074).
Both Node jobs also passed prepare, type checking, static generation and 62
core/artifact tests. The viewer supports the tested local JSON import, keyboard
transport and procedural rendering paths; its native file button now uses stable,
readable theme colors without color interpolation.

This is candidate evidence for [issue 32](https://github.com/patchwerks/furbomek/issues/32),
not final PR acceptance or a comprehensive accessibility audit. PR 41 was
accepted and merged on 2026-11-04 at
`ccad3d5c9cd9d52c83af20e21163dbd4b0ea8463`. PR 42 independent review,
retargeting to accepted main and fresh exact-head checks remain required. The [original candidate record](extension-viewer-2026-11-02.md)
preserves the earlier implementation evidence.

## Exact tested scope

| Build runtime | Chromium 156.0.8078.4 | Firefox 157.0 | Core/artifact tests |
|---|---|---|---|
| Node 22.22.3 / npm 10.9.8 | 30 passed | 30 passed | 62 passed |
| Node 26.7.0 / npm 11.19.0 | 30 passed | 30 passed | 62 passed |

All four browser result files report no outbound requests and no uncaught browser
errors. The 30 scenarios comprise 24 baseline/rendering/contrast checks and six
keyboard checks. Browser versions above are actual `browser.version()` results,
not inferred from the package version.

Each artifact's `candidate-sha.txt` identifies tested source
`87a50b335a58dea2b4920a53afd14913de405765`; `enforcement-sha.txt` identifies
accepted enforcement `cdd9147fac9141fa0c75b5058f9dce46c7885188`. Artifact names
contain workflow merge-ref SHA `c28ad7d3018dbea453b9426725d09619346d810c`,
which must not be mistaken for the source checkout. At qualification time PR 42
was stacked on then-unaccepted PR 41 source
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28`; that exact dependency is now accepted.
The documentation child `92b7c14699d125177bd3f01d896b25ebe3ffa02b` subsequently
passed [run 41408868444](https://github.com/patchwerks/furbomek/actions/runs/41408868444).
Neither historical run qualifies a newly rebased final-main head.

Qualification used the existing two Linux Node builds, provisioning and compiling
once per job, followed by separate disposable Chromium and Firefox workers.
Playwright is pinned to 1.64.1 and browser image
`mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea`.
Chromium used its headless ANGLE/SwiftShader path. Firefox used headed Xvfb,
1600×1200×24 virtual screen, `LIBGL_ALWAYS_SOFTWARE=true` and
`GALLIUM_DRIVER=llvmpipe`, without Chromium flags or Firefox preferences.
Firefox logs record Mesa 25.2.8 and Xvfb 21.1.12. Actual WebGL2 reports show
876×570 drawing buffers; Firefox reports `llvmpipe, or similar`, while Chromium
reports ANGLE Vulkan/SwiftShader. These are the tested Linux software-rendering
paths, not qualification of arbitrary devices, operating systems or browsers.

## Behavior and rendered contrast

The original 23 scenarios remain: actual WebGL2, rendered expression and reaction
changes, same-browser reduced-motion/neutral pixel equality, deterministic early
RAF handling, seek/play/pause/reset/end, invalid/oversize/unauthorized/unreadable
and stale imports, filename escaping, hidden-document pause, context loss,
explicit WebGL unavailability, unmount/resource release, and dark link contrast.
No fake renderer or cross-browser pixel-equality requirement is used.

Keyboard tests use actual Tab in DOM order (Play, Reset, Timeline, Import,
Example, footer) and Shift+Tab to return to earlier controls. They check visible
focus and viewport bounds, native Space file-picker activation, Enter example
loading, Space/Enter transport, native Home/Arrow/End range behavior and accessible
value text, reset/end neutrality, and 390-pixel traversal without overflow.
They allow bounded native focus scrolling to settle, never directly focus or
scroll a control, and do not require wraparound through browser chrome. These
checks do not cover assistive technology or establish full WCAG conformance.

The file-selector button uses existing `--stage`/`--ink` colors normally and
`--line`/`--ink` on hover, with `appearance: none; transition: none`. The real
file input/picker and all native keyboard tests remain. Its additional contrast
scenario hovers the input and captures `file-selector-hover.png`; unsupported or
transparent computed colors fail instead of silently skipping the assertion.

All four final results record foreground RGB(237, 240, 243), background
RGB(73, 82, 91), appearance `none`, transition property `none`, actual hover true,
and computed contrast **6.950862417:1**. Coordinator decoding of each actual hover
PNG found the same dominant background RGB(73, 82, 91) in the bounded button
interior sample (x 3–65, y 3–30). Its contrast against the recorded light foreground
is also **6.950862417:1**. This confirms the sampled raster background matches the
authored color in all four artifacts; it is not a claim that antialiased text-edge
pixels all have that ratio.

The coordinator visually inspected both final engine hover PNGs and final Firefox
dark desktop: labels were readable and coherent. Earlier Firefox light, mobile
and mid-cue screenshots of the same layout/renderer were also inspected; the final
change only affects the file-button styling. Computed colors alone were not used
to accept the final rendered state.

## Evidence and execution boundary

Build logs stay at artifact root; browser logs, observed version, diagnostics,
WebGL report, results and five screenshots stay in separate `chromium/` and
`firefox/` directories. Each browser has a separate profile/cache and ephemeral
`/tmp`. Candidate code runs only in credential-free, network-none disposable
workers; the publisher host did not execute dependencies, builds or browser tests.
The reviewed export validator allows exact directory/file names, rejects symlinks
and nonregular files, and limits each file to 8 MiB and each job to 32 MiB.

Observed local inert checks included JavaScript syntax, safe YAML parsing,
embedded Python syntax, shell syntax and diff whitespace. These complement the
hosted checks; they are not runtime qualification by themselves. No deployment,
live connection, hardware action or issue closure follows from this evidence.
Rollback is reverting this compatibility/test/theme follow-up; root dependencies,
renderer and parser/sampler are unchanged.

## Evidence history

- [First probe 41396867865](https://github.com/patchwerks/furbomek/actions/runs/41396867865),
  source `a9fdf722ed3fa7e09957ff79e1d1b44e62c78169`, failed keyboard checks;
  Firefox did establish actual WebGL2. Artifact merge ref was
  `e510c5930c41a61bd7dc49be596671b8889c7411`.
- Second probe source `58d9e83930cd9429f7a34078eb7f0c6c9e1f794c` passed
  Chromium 29/29 and Firefox baseline 23/23 on both builds, but Firefox's overall
  result failed because the test demanded forward-Tab wraparound through browser
  chrome. Artifact merge ref was `904c065f403ffe4a0a6b1d5401d6876504fb0865`.
  Inspection justified the in-page forward/reverse route now tested.
- [Run 41398180108](https://github.com/patchwerks/furbomek/actions/runs/41398180108),
  source `860d445bf1468728f12d5c3325bc765ee0d6990c`, passed all 29 cases in
  all combinations. Visual review then found poor native file-button contrast.
- [Run 41406368411](https://github.com/patchwerks/furbomek/actions/runs/41406368411),
  source `758d425c1999d64ee07fceaa78a6762029eaab9e`, passed 30 cases but
  Firefox's actual button raster did not match computed colors. Appearance-only
  suppression also left varying raster backgrounds and inadequate Firefox
  contrast. Native-overlay causality was unproven; these remain failed visual
  evidence, not superseded claims of visual acceptance.
- The final source/run above adds immediate file-button color changes and passes
  both the unchanged 30-case matrix and coordinator raster/visual review. The
  observed final stability is established; earlier causal hypotheses are not.

## Primary references

- [Pinned Playwright browser manifest](https://github.com/microsoft/playwright/blob/v1.64.1/packages/playwright-core/browsers.json),
  [Docker contents](https://playwright.dev/docs/docker), and
  [headed CI/Xvfb](https://playwright.dev/docs/ci#running-headed).
- [Mesa software-rendering variables](https://docs.mesa3d.org/envvars.html).
- Mozilla's [appearance](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/appearance)
  and [file-selector button](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Selectors/::file-selector-button)
  references; actual tested behavior is recorded above.

## Changelog

- 2026-11-04: Recorded PR 41 acceptance and the qualified documentation child; retained exact historical source evidence and pending PR 42 final-main review/checks.

- 2026-11-02: Prepared bounded Firefox/keyboard qualification and recorded failed
  probes, corrected navigation acceptance, and investigated rendered contrast.
- 2026-11-02: Consolidated the final four-way 30-case evidence, exact source and
  enforcement identities, stable sampled raster contrast and coordinator visual
  review; preserved independent acceptance and integration gates.
