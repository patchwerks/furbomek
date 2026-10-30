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
uses that getter. The initial identity guard was superseded by detached snapshots
and a content guard in the maintainer follow-up below. See [Vue's prop guidance](https://vuejs.org/guide/components/props).

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
dependency graphs are not unchanged. The initial qualification retained Nuxt ESLint 0.4.0; the follow-up below updates
that parent to 0.7.6. Nested Nuxt kit 3.21.11 remains alongside framework kit 4.6.3. The lock also contains nested vue-tsc
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

## ESLint parent compatibility follow-up

Starting from combined PR #28 head
`330ff80111a9eaad84929d6d15527ec7cc93eec7`, the root Nuxt ESLint module is pinned
to 0.7.6. This is the first published parent accepting inspector 1.x while retaining
ESLint 8 support. The resolved inspector moves from 0.5.6 to 1.3.0 and its nested
esbuild from 0.24.2 to 0.25.12; the separate esbuild 0.28.2 remains unchanged.
No overrides or forced peer resolution are used. The 0.5.x inspector series has
no release using patched esbuild. See the official
[Nuxt ESLint release](https://github.com/nuxt/eslint/releases/tag/v0.7.6),
[parent metadata](https://registry.npmjs.org/@nuxt%2feslint/0.7.6), and
[inspector metadata](https://registry.npmjs.org/@eslint%2fconfig-inspector/1.3.0).
This removes the affected version gap for
[GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99);
the advisory requires esbuild's development serving API. Its use was not
established in the inspected inspector build/watch path. No development server
or inspector listener was started for qualification. Inspector 1.3.0 is a conscious
lock selection within the parent's supported `^1.0.0` range: its esbuild `^0.25.9`
range avoids the newer Windows serving regression
[GHSA-g7r4-m6w7-qqqr](https://github.com/advisories/GHSA-g7r4-m6w7-qqqr).
Normal npm registry resolution produced the package objects; the final manifest
has no direct inspector dependency or override. `npm ci` preserves this selection;
a future `npm update` may select inspector 1.5.0/esbuild 0.27.x again and must be
reaudited. This is not an all-advisories-cleared claim.

Lockfile SHA256:
`cf1ea75c24516aff2173f01b86e604111faaeb9a8fcaff361b4c734d32af1df4`.
The graph changes 64 retained package records, adds 48 and removes 164 paths.
Changes are the lint dependency closure plus deduplication: 28 removed helper
paths outside that closure resolve to hoisted copies with identical versions and
integrity hashes. Direct Nuxt, Vue, router, Bootstrap, provider SDKs, TypeScript
and root ESLint 8.57.1 remain unchanged. No application/configuration source changed.

Fresh offline script-disabled install, production build with configured types,
direct vue-tsc, configuration/Settings/boundary checks and offline browser smoke
pass on the same Node 26.7.0/macOS arm64 worker. Eleven shared public output files
remain byte-identical to the combined baseline; only build metadata changes.
All browser functional assertions pass with zero page/console errors, unknown
requests or missing assets. Focus-return samples remain diagnostic, not a guaranteed behavior or acceptance
assertion.

The module remains enabled and generates usable `.nuxt/eslint.config.mjs`.
ESLint 8 loads the real generated config, calculates the Vue configuration, and
reports an expected fatal parse diagnostic for a malformed synthetic Vue/TS input.
Native `unrs-resolver` also resolves Vue with Node/require/default conditions after
the script-disabled install. Baseline and candidate app lint both report 11 errors
and 20 warnings with no fatal errors: existing lint debt, not a clean-lint claim.
The upstream TypeScript ruleset changes from 204 to 209 rules, replacing older
rules such as ban-types/no-var-requires with their successor rules. No project
rules are disabled or source suppressed to obtain this result. Independent review,
exact new-head hosted checks and maintainer acceptance remain separate gates.

## Remaining dependency finding for maintainer disposition

A fresh metadata audit of the final graph reports no moderate, high or critical
findings. Its eight low package entries trace to one underlying advisory,
[deepmerge GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4).
Deepmerge 4.3.1 remains through the active Deepgram SDK and build-time Rollup
node-resolve plugin; no compatible patched release is identified. This finding
is unresolved, not accepted risk or an alert dismissal.

The [upstream report](https://github.com/TehShrike/deepmerge/issues/273) describes
attacker-controlled merge inputs/target shapes producing inherited properties;
downstream use of those properties is necessary for impact. The active SDK merges
client configuration with built-in defaults. Static inspection did not find merges
over provider transcript/response bodies. Normal settings have fixed fields, but
same-origin localStorage restoration lacks runtime schema validation, so malformed
persisted configuration cannot be ruled out. No unauthenticated remote storage
writer or application exploit was established; this is not a complete taint proof.
The inspected Rollup call merges only hardcoded defaults; plugin options use object
spread. A separate settings-validation boundary or parent replacement would need
its own security/compatibility review. No advisory-evading downgrade, fork or
removal of the active provider is included. Maintainer disposition remains required.

The portable Settings regression is
`node tools/legacy-compat/settings-regression.cjs`. It compiles the real SFC and
settings defaults and checks detached provider snapshots, deep parent updates,
complete/partial/reordered replacements and default-array immutability, including an equivalent-normalized partial replacement. The
expanded sequence expects six bounded emissions with cleanup.

`node tools/legacy-compat/render-spa.mjs .output > rendered.html` renders the
built SPA in process without opening a listener. A test-only transport stub
intercepts the node-server preset's import-time listen call; it does not alter
generated HTML or application assets. The renderer checks the generated
Nitro accessor and fails if that build format changes. It restores the original
listener in `finally`, including import, fetch and assertion failures; run
`node --test tools/legacy-compat/render-spa.test.mjs` for six no-socket fixtures.

`tools/legacy-compat/browser-smoke.cjs` takes a rendered SPA HTML file and its
matching production public directory. Playwright is external test tooling;
`PLAYWRIGHT_MODULE` and `CHROMIUM_EXECUTABLE` can identify an existing installation.
Run only in a restricted worker. It serves files through interception, supplies
explicit local provider fixtures (including an inert warning-only voice), asserts blank credential headers, aborts
unknown requests and stubs media devices/AudioContext/WebSockets before app load.
It checks blank-provider send guards, input mode, all four settings tabs, modal
open/close/reopen, backdrop non-dismissal, repeated persisted edits and errors.

Existing startup attempts to list assistants/voices and read subscription state,
and the explicit synthetic out-of-credits fixture, are fulfilled locally; they are not live provider tests. No microphone, audio
output, hardware, OBS, production service or deployment is exercised. The test
worker denies TCP/IP and user-home/device data access; Chrome-owned temporary
Unix IPC is permitted. Chromium's inner sandbox is disabled because nested
sandbox startup fails, while the mandatory outer OS restrictions remain active
and are probed. Private logs and security inventory are not part of this change.

Independent review, final-head hosted checks, maintainer acceptance and subsequent
alert verification remain required. Roll back by restoring this candidate's
manifest, lock and compatibility source changes together to its PR #23 base;
retain DevTools disabled. No service or device has been changed by this work.


## Maintainer review follow-up (2026-10-30)

**Observed:** the previous guard emitted the child's reactive object directly.
After the first v-model echo, a second child edit mutated the previous parent
snapshot before Vue's next tick. Parent deep edits leaked immediately into the
child, and an array edit after partial-default completion could mutate
`defaultSettings`. That breaks `app.vue`'s previous/new provider-setting
comparison.

The child now JSON-clones normalized inputs/defaults and outgoing snapshots.
Sorted object keys make the content guard insensitive to property insertion order;
array order remains significant. This uses the existing JSON-persisted Settings
contract, not a new validation/schema boundary. Complete parent replacements and
deep parent changes synchronize without an unnecessary emission; incomplete
external replacements emit completed defaults once, even when their normalized
content equals the current child state. Local changes replace the parent's object
and preserve previous provider values. No provider implementation or persistence
schema changed.

The Vue manifest floor is now `^3.5.0`, matching the reactive destructured prop
behavior used by the SFC. Only root manifest/lock metadata changed: every
installed package record, including Vue 3.5.44, is identical to `ef06a8c`.
Nuxt/provider versions, inspector 1.3.0 selection and the unresolved deepmerge
finding remain as recorded above.

**Observed validation:** strict credential-free macOS arm64 worker, Node 26.7.0
and the existing npm 10.9.2-installed dependency tree: production build including
types, direct vue-tsc, expanded compiled Settings regression and six renderer
success/failure tests pass. The expanded Settings test fails against the prior
source on shared-reference ownership; five renderer error-path cleanup tests fail
against the prior renderer and pass with `finally`. Home/device read and loopback
TCP-denial probes pass. Dependency records did not change; this follow-up reused
the previously qualified install rather than claiming a new clean install.

The production browser fixture also verifies that two successive ElevenLabs
stability edits each invoke the parent's provider watcher and refresh empty local
voice fixtures, with blank credentials throughout. Settings keyboard Enter/open,
Enter/close, Escape/close, transition-settled focus return, backdrop non-dismissal
and 1280/390 viewport screenshots and scroll-to-footer reachability are checked.
The fixture sees no page errors, unexpected console errors, missing assets or
unknown requests. The browser resource diagnostic for the intentional 403 on the
exact intercepted PlayHT stream URL is expected. This is agent-operated fixture
validation and visual inspection, not human manual acceptance or live-provider
qualification. The earlier focus variability was reproduced when the test
interacted after visibility but before BModal's enter-transition focus-trap
activation. Its trap then remembered an in-modal target, leaving focus on BODY
after close. The final harness waits for the modal's initial focus before
interacting, then asserts the Settings button receives focus after pointer close
and keyboard Escape/Enter. No product focus override or disabled-trap workaround
was added. A synthetic PlayHT voice and intercepted 403 `OUT_OF_CREDITS` fixture
exercise warning display, default sizing at both widths, backdrop non-dismissal,
Escape/close and reopening. AudioContext remains inert and the POST never leaves
request interception; the real provider/out-of-credits path is unqualified.

**Merge/CI gate:** PR #28 must land after independently accepted PR #22 supplies
the Node 26.7.0 worker; PR #18's Node 22.16.0 does not meet the declared floor. No
workflow or engine-floor change is made here. Existing hosted CodeQL results are
not a Linux CI build/type/browser qualification. That worker qualification,
maintainer UI acceptance and exact changed-head checks remain outstanding.

**Proposed follow-up under issue #13:** migrate the root lint runtime to a
currently maintained ESLint major (9+ compatibility scope, select a supported
release at implementation time) with a compatible Nuxt ESLint parent. ESLint 8 is
EOL; the nested ESLint 10.13.0 tooling copy does not upgrade the root 8.57.1
runtime. The repository already uses flat config via `eslint.config.mjs` and the
generated `.nuxt/eslint.config.mjs`; this is a runtime/plugin compatibility
upgrade, not a pending conversion from `.eslintrc`. See the official [ESLint
support notice](https://eslint.org/blog/2024/09/eslint-v8-eol-version-support/)
and [Nuxt ESLint flat-config
documentation](https://eslint.nuxt.com/packages/module) (accessed 2026-10-30).

That separate slice must inventory peer/engine requirements, preserve generated
Vue/TypeScript rules, compare baseline diagnostics (11 errors/20 warnings in the
prior app qualification), exercise malformed Vue/TS parsing and native resolver
behavior, then run build/types and the accepted Linux worker. Reaudit inspector
and both esbuild paths while preserving the explicit 1.3.0 selection until a
replacement is qualified. Do not disable rules, suppress existing debt, or force
peer/major overrides to make the migration pass. This is a documented plan, not an
implemented migration or an accepted long-term ESLint 8 support decision.
