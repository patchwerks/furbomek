---
created: 2026-10-29T21:00:34Z
branch: codex/13-nuxt-compat
author: Codex
status: active
---
# Legacy Nuxt compatibility qualification

References [issue 13](https://github.com/patchwerks/furbomek/issues/13). This
candidate moves the legacy browser application onto Nuxt 4 while retaining its
root directory layout, SPA mode, disabled DevTools, existing settings schema and
provider interfaces. It was built on the unmerged PR #23 candidate at
`016e577e6c5be0f9dea86025e938c91d3eaf60ce`; published main was verified at
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. Draft PR #28 targets main so the
repository's existing default CodeQL checks run. Its ancestry includes PR #23's
already reviewed containment changes, still pending independent maintainer
acceptance; this does not imply that #23 is merged. This candidate now incorporates
PR #24's unused root PlayHT npm SDK removal directly into the Nuxt 4 lockfile.
PR #24 remains unchanged and open; its older lockfile must not replace this graph.
The local `PlayHtTTS` implementation, proxy calls and settings remain present.
The separate CI/bootstrap PR #22 now carries a reviewed Node 26.7.0 worker pin
at `d38d12d8a468f002dc1a869de50f838cbe7cf8fb`; PR #18 remains unchanged.
This meets the declared framework floor, but maintainer acceptance and full Linux
Docker/proxy qualification remain separate gates. No CI workflow is changed here,
and local macOS results do not qualify that operational worker.

## Why this compatibility change is necessary

[Nuxt 3's final release](https://github.com/nuxt/nuxt/releases/tag/v3.21.11)
identifies that line as end-of-life. The reviewed
[Nuxt 4.6.3 release](https://github.com/nuxt/nuxt/releases/tag/v4.6.3) includes
current framework security fixes. Exact published registry metadata requires
Node `^22.22.3 || ^24.15.0 || >=26.0.0`; the root manifest now records that floor.
Testing used Node 26.7.0, not every allowed runtime.

| Component | Baseline | Candidate |
|---|---|---|
| Nuxt | 3.12.4 | 4.6.3 |
| Framework Vite | 5.3.5 | 8.3.5 |
| Nitro | 2.9.7 | 2.13.5 |
| Vue / router | 3.4.34 / 4.4.0 | 3.5.44 / 5.4.0 |
| Nuxt DevTools dependency | 1.3.9 | 3.4.4, still disabled |
| BootstrapVueNext Nuxt module / runtime | 0.24.2 / 0.24.2 | 1.0.0 / 1.2.2 |
| TypeScript / direct vue-tsc | 5.5.4 / 2.0.29 | 5.9.3 / 3.3.9 |

The old Bootstrap Nuxt module explicitly requires Nuxt 3 and is disabled by Nuxt
4. The supported module installs its official `createBootstrap` plugin;
no custom compatibility override or new BApp wrapper is needed. The two existing
inline modals now use boolean `v-model` refs, retaining their named show functions
and contents. The warning modal uses the normal default size instead of the
removed `md` value. See the official
[Nuxt setup](https://bootstrap-vue-next.github.io/bootstrap-vue-next/docs) and
[modal API](https://bootstrap-vue-next.github.io/bootstrap-vue-next/docs/components/modal).

Vue 3.5 requires a getter when watching a destructured prop. The settings watcher
now uses that getter and ignores its own identical-reference v-model echo before
merging externally replaced settings. This prevents a fresh-object feedback loop
while retaining deep updates. See [Vue's prop guidance](https://vuejs.org/guide/components/props).

TypeScript 5.5 cannot parse current dependency declarations or the generated
`libReplacement` option ([introduced in 5.8](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-8.html)).
The existing PlayHT buffer helper's parameter now accepts `ArrayBufferLike`,
matching its existing DataView use. Its complete emitted JavaScript is identical;
audio queue, scheduling, byte-view handling and provider source logic are unchanged.
Live provider behavior remains unqualified because dependency transitives refresh.
The OpenAI adapter now explicitly imports its declaration-only Thread/Message
types and accurately types the messages.create promise, removing an old
`@ts-ignore` and invalid runtime import artifact. Its operational JavaScript is
also identical under common TypeScript erasure (comments excluded). No request,
event, stream or cancellation logic changed.
No casts, `any` suppression or weaker type-check options were added. Existing
root tsconfig relaxations remain pre-existing limitations.

Only `mergeDeep` from `@unocss/core` is used by the application. The unused UnoCSS
aggregate is replaced with the same exact core 0.61.6, removing its old Vite plugin
closure without changing the imported utility. Direct Deepgram 3.5.0, OpenAI
4.53.2 SDK versions are retained. The initial Nuxt qualification also retained
PlayHT 0.9.8; the combined follow-up below removes that unused npm SDK. The Nuxt
upgrade refreshed transitive dependencies, including HTTP, WebSocket and helper
packages; the provider
dependency graphs are not unchanged. Nuxt ESLint 0.4.0 remains, with a nested Nuxt
kit 3.21.11 alongside framework kit 4.6.3. The lock also contains nested vue-tsc
3.3.14 in addition to direct 3.3.9. This is not a claim that every security alert
has been remediated.

## Verification status

Observed on macOS arm64 with Node 26.7.0 and npm 10.9.2:

- Baseline and candidate real production builds pass, including configured type
  checks. Candidate direct `vue-tsc --noEmit -p tsconfig.json` also passes using
  root vue-tsc 3.3.9. The build closure additionally contains vue-tsc 3.3.14;
  no claim is made that every build-internal checker resolves to the root copy.
- Final fresh `npm ci --offline --ignore-scripts --no-audit --no-fund` passes.
  Dependency preparation used blank npm configuration and disabled lifecycle
  scripts. The unrelated root postinstall/server installation hook was not run.
- Actual Nuxt configuration loading confirms DevTools disabled, `ssr: false` and
  root `srcDir`. No development server or RPC was started.
- The compiled Settings setup regression passes local edits, external prop
  replacement and a repeated edit with exactly three bounded emissions. An
  independent reviewer reproduced it from hash-matched sources.
- Baseline and candidate pass the same browser smoke: blank-provider send guards,
  input mode, all four tabs, modal open/close/reopen, actual pointer clicks outside
  modal content without backdrop dismissal, and repeated persisted settings edits.
  Both produce zero page/console errors, missing assets or unknown external
  requests. The same five GET attempts receive explicit empty local fixtures;
  provider credential headers are asserted blank. Focus return was observed as
  false/false on the baseline and true/true on the candidate; this is a changed
  Bootstrap modal default, not an unchanged-behavior assertion.
- Separate common-TypeScript erasure comparisons show unchanged operational
  JavaScript for the touched PlayHT and OpenAI adapter sources (OpenAI comments
  excluded). This does not claim framework bundles or provider dependency graphs
  are byte-identical.
- Outer worker boundary probes confirm user-home/device file-open and loopback
  TCP denial. CRLF-aware whitespace checks pass, preserving existing line endings.

Initial Nuxt-only package-lock SHA256:
`50d74907c6c51b6f32e7ce7fac085861d67398fec4eb3a3bd095ff522243f81a`.
Compared by package path with the baseline: 489 added, 348 removed and 399 retained
paths changed version. These are dependency graph counts, not advisory counts.
No Linux/Windows runtime, alternate Node version or live provider acceptance is
claimed. Hosted checks and maintainer acceptance remain separate.

## Combined unused PlayHT SDK removal

The reconciliation starts from PR #28 head
`25c6593ac6b350a89cfb1940acf1058c5efe03df`, not PR #24's older dependency graph.
Only the root `playht` dependency and its 28 orphan lockfile package paths are
removed. No package paths are added. Every retained package version, integrity,
resolution and dependency field is identical. Five retained packages (`cliui`,
`yargs`, `wrap-ansi`, `yargs-parser`, `require-directory`) gain only `dev: true`,
reflecting their remaining development-only reachability. Application source,
including the local PlayHT streaming integration, is unchanged from #28.

Combined package-lock SHA256:
`450a19c6285619bada0ea2fb6e9bbf9535304829ab2a34e3bce421301ad42dae`.
A distinct credential-free worker passed fresh offline lifecycle-disabled install
(1,101 packages), configured production build, direct root vue-tsc, actual Nuxt
configuration assertions, compiled Settings regression and the same offline
browser smoke. Home/device/TCP denial probes pass under the unchanged policy.
The browser uses the same five explicitly empty provider fixtures with blank
credential headers; no unknown requests, page errors, console errors or missing
assets were observed. No live provider qualification is implied.

All 11 shared production public files, including client JavaScript and CSS, are
byte-identical to the preserved #28 output. Only generated build metadata IDs and
timestamps differ. Focus-return observations are diagnostic and timing-sensitive;
both the preserved #28 rerun and combined run recorded `[false, true]`, compared
with the earlier `[true, true]` Nuxt candidate sample. Focus return is not an
acceptance assertion. The Node/platform and independent
maintainer/hosted-check limits above still apply to this combined candidate.

The portable Settings regression is
`node tools/legacy-compat/settings-regression.cjs`. It compiles the real SFC and
settings defaults, exercises local edits, an externally replaced prop and a
second edit, and checks exactly three bounded emissions with cleanup.

`node tools/legacy-compat/render-spa.mjs .output > rendered.html` renders the
built SPA in process without opening a listener. A test-only transport stub
intercepts the node-server preset's import-time listen call; it does not alter
generated HTML or application assets. The renderer checks the generated
Nitro accessor and fails if that build format changes.

`tools/legacy-compat/browser-smoke.cjs` takes a rendered SPA HTML file and its
matching production public directory. Playwright is external test tooling;
`PLAYWRIGHT_MODULE` and `CHROMIUM_EXECUTABLE` can identify an existing installation.
Run only in a restricted worker. It serves files through interception, supplies
explicit empty local provider fixtures, asserts blank credential headers, aborts
unknown requests and stubs media devices/AudioContext/WebSockets before app load.
It checks blank-provider send guards, input mode, all four settings tabs, modal
open/close/reopen, backdrop non-dismissal, repeated persisted edits and errors.

Existing startup attempts to list assistants/voices and read subscription state
are fulfilled locally; they are not live provider tests. No microphone, audio
output, hardware, OBS, production service or deployment is exercised. The test
worker denies TCP/IP and user-home/device data access; Chrome-owned temporary
Unix IPC is permitted. Chromium's inner sandbox is disabled because nested
sandbox startup fails, while the mandatory outer OS restrictions remain active
and are probed. Private logs and security inventory are not part of this change.

Independent review, final-head hosted checks, maintainer acceptance and subsequent
alert verification remain required. Roll back by restoring this candidate's
manifest, lock and compatibility source changes together to its PR #23 base;
retain DevTools disabled. No service or device has been changed by this work.
