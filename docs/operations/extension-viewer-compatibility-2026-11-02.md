---
created: 2026-11-02T05:52:55Z
branch: codex/32-browser-viewer
author: patchWERKS / Codex
status: active
---
# Issue 32 browser compatibility and keyboard candidate

**Proposed, not runtime-qualified.** This follow-up extends the viewer candidate
at `5090832a218e17439bd74e6b4beaad4b770d512e` (PR 42), stacked on
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28` (PR 41). Both remain unaccepted;
accepted enforcement remains `cdd9147fac9141fa0c75b5058f9dce46c7885188`.
The [previous candidate record](extension-viewer-2026-11-02.md) preserves the
observed Chromium evidence. This record does not upgrade those results to Firefox
compatibility or full accessibility acceptance. Canonical work is
[issue 32](https://github.com/patchwerks/furbomek/issues/32).

## Proposed qualification

The two existing Node 22.22.3 / 26.7.0 jobs each provision and compile once.
Each then runs Chromium and Firefox sequentially in separate disposable,
credential-free, network-none browser workers against that same compiled output.
A browser failure does not prevent the other browser's attempt or evidence export;
the job fails if either attempt fails. Root manifests, application, renderer and
parser/sampler are unchanged.

Playwright stays pinned to 1.64.1 and image
`mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea`.
The [pinned browser manifest](https://github.com/microsoft/playwright/blob/v1.64.1/packages/playwright-core/browsers.json)
names Firefox 157.0 revision 1555 and Chromium 156.0.8078.4 revision 1248;
these are reference versions, not a substitute for observed `browser.version()`.
Actual versions are recorded separately in each browser's evidence directory.
The [Playwright Docker documentation](https://playwright.dev/docs/docker)
explains that the image includes browsers and their system dependencies while the
Node package must be installed separately; the existing hash-checked tarball
provisioning remains unchanged.

Chromium retains its existing headless SwiftShader flags. Firefox uses headed
mode under Xvfb with a 1600×1200×24 virtual screen, consistent with the
[official CI guidance](https://playwright.dev/docs/ci#running-headed).
The worker first checks Xvfb, Mesa package versions and the software driver file.
`LIBGL_ALWAYS_SOFTWARE=true GALLIUM_DRIVER=llvmpipe` selects Mesa software
rendering using [documented Mesa variables](https://docs.mesa3d.org/envvars.html).
No Chromium flags or Firefox preferences are passed to Firefox. This configuration
is a proposed hosted probe; the pinned image's successful rendering is still TBD.

Both browsers must pass a real WebGL2 drawing-buffer check, rendered cue changes,
acknowledgment transforms, and neutral/reduced-motion pixel equality within the
same browser. Cross-browser screenshot equality is not asserted. WebGL failure
is a failed positive test, never a substitute 3D success. The deliberately disabled
WebGL test runs first and verifies the explicit error, disabled Play and missing
canvas; its result is retained if the later positive test fails.

The original 23 scenarios remain, including stale/invalid imports, unmount and
context loss, early RAF timestamps, outbound requests and forbidden capabilities.
Six additional named scenarios exercise actual keyboard input:

- Tab reaches import, example, transport, timeline and footer, with a visible
  focus outline and a control inside the viewport; reverse Tab leaves import.
- Enter opens the native file chooser and imports the real bundled fixture.
- Enter restores the bundled example.
- Space/Enter activate play, pause and reset; paused time stays fixed and reset
  returns to neutral at zero.
- Home, ArrowRight, ArrowLeft and End drive the native range with the actual
  one-millisecond step and matching accessible value text; playback from the end
  restarts, and keyboard reset returns to neutral.
- The same traversal works at 390-pixel width, reaches controls again after the
  footer, and introduces no horizontal overflow.

This is 29 planned browser scenarios per browser/build combination, not 29 tests
already observed passing. It is bounded keyboard regression coverage, not an
assistive-technology or comprehensive WCAG audit.

## Evidence boundary and current result

Build logs stay at the evidence root. Browser logs, observed version, renderer
failure diagnostics, WebGL report, results and the four existing screenshots go
under separate `chromium/` and `firefox/` directories. Profiles and caches are
separate, and each worker has its own ephemeral `/tmp`. The trusted export step
allows only the two directory names and exact file names, rejects symlinks and
nonregular files, and preserves 8 MiB per-file / 32 MiB per-job limits.

**Observed locally:** JavaScript syntax check, Ruby Psych safe YAML parse,
embedded Python syntax compile, shell syntax check and diff whitespace check.
Python's optional YAML module is absent on the host; Ruby performed the inert
YAML parse. No dependency hook, app build, browser installation, app server or
candidate test executed on the publishing host.

**TBD:** independent workflow/export review, actual hosted Node/build/browser
results, visual inspection of both browsers' artifacts, and fresh exact-head
review. A failure requires its actual diagnostics and at most one focused retry
before reassessing the claimed compatibility. No runtime compatibility or full
accessibility claim is authorized by this proposal alone.

Rollback is removal of this test/workflow follow-up; it installs or deploys no
application or hardware changes. PR acceptance, retargeting to accepted main and
issue closure remain separate gates.
