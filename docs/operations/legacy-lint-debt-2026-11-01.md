---
created: 2026-11-01T07:58:12Z
branch: codex/30-lint-debt
author: madeleine-lgtm / Codex
status: active
---
# Legacy application lint debt — issue 30

This follows [issue 30](https://github.com/patchwerks/furbomek/issues/30) and
accepted ESLint upgrade PR35. The source base is published main
`cdd9147fac9141fa0c75b5058f9dce46c7885188`.

## Scope and behavior preservation

The patch types select options, provider voice/subscription responses, stream
reader promises and event callbacks. `ChatEvent` remains an exported runtime
class with the same inheritance and constructors; its optional `message`
declaration is type-only and emits no property. Callback return values remain
ignored. The browser process compatibility assignment remains the same object.

Explicit `if` statements retain the existing truthiness and order of chat/TTS
side effects. No awaits, cancellation logic or queue operations are added.
Only unused literal initializers are removed: the local empty `prevDelta`
shadow and `HEADERS_SIZE = 78`. The actual outer delta ref remains unchanged.
The existing `created` listener versus `create` emission mismatch is outside
this cleanup and is preserved.

Vue template changes reorder attributes, hyphenate a prop and self-close empty
nodes without changing layout, text, styles or bindings. The settings component
gets explicit multi-word metadata name `ProviderSettings`; this changes its
devtools/component name, not its props or rendering. Avatar entrypoints explicitly
read `globalThis.FurbomekView`, matching the existing renderer export.

No dependency, lockfile, ESLint configuration, rule severity, suppression,
workflow, service, CI helper or shared governance file changes are included.
No new images or visual redesign are included.

## Qualification record

**Observed prior evidence:** PR35 run
[41243857696](https://github.com/patchwerks/furbomek/actions/runs/41243857696)
reported 36 errors / 23 warnings repository-wide and 11 errors / 18 warnings in
`app.vue`, with zero fatal diagnostics, on its final head
`b2dc72d89d464d883361551502b4f553b32d5946`, subsequently merged at the base above.
These are historical baseline observations, not a fresh run of this patch.

**Pending:** exact-head hosted lint, production build/type checks, full offline
install and avatar browser fixture results. No candidate JavaScript, dependencies
or install hooks were executed on the credentialed host. The existing accepted
ESLint qualification workflow can be dispatched on the branch unchanged; its
embedded older ESLint8 baseline must not be confused with this patch's base.
Candidate lint exit codes and zero diagnostic counts must be checked directly,
because that advisory workflow permits pre-existing debt. The existing avatar
workflow supplies real offline tests and browser fixtures on the changed files.

Live microphone, provider accounts, audio devices, OBS and robot hardware are
not exercised. This software cleanup does not qualify their lifecycle behavior.

## Rollback

Revert this source/doc change on an accepted revision; retain PR35's supported
ESLint dependency stack and configuration. No installed runtime is changed.

## Changelog — 2026-11-01

First qualification [41287125795](https://github.com/patchwerks/furbomek/actions/runs/41287125795)
on head `1c3fda4935bf43ff1147cd209947aeab1f955da9` reached the production build
on both Node22.22.3 and Node26.7.0, then failed with TS4115 on the two message
constructor parameter properties. Explicit type-only `override` modifiers correct
that declaration requirement; constructors and emitted properties stay the same.
Lint had not run for the candidate at this failure, so no candidate count is
claimed from that run. This is focused correction attempt one.

The same head passed [avatar fixtures 41287127067](https://github.com/patchwerks/furbomek/actions/runs/41287127067):
15 unit tests, zero failures, and the real offline browser checks for the bundled
asset, labelled fixture, interruption/expiry, literal HTML text, no global live
instance and no page errors. All displayed CodeQL checks also passed.
`npm run generate` is not included in the reused lint workflow and has not been
freshly run for this cleanup. Final corrected-head qualification remains pending.

## Qualification update — 2026-11-01

Corrected source head `e9fe7d6a31a5dee6af1cb5462a32c4c6a3cd2931` passed
[41292033486](https://github.com/patchwerks/furbomek/actions/runs/41292033486)
on both Linux Node22.22.3/npm10.9.8 and Node26.7.0/npm11.19.0. Actual artifact
JSON records **zero errors, warnings and fatal diagnostics** for both `app.vue`
and the whole repository on both versions. Each `candidate-status.txt` is
`0 0 0`: app lint, repository lint and dependency-tree inspection all exited0.
The previous app11/18 and repository36/23 debt is removed without suppression.

Both jobs completed production build with configured type checks, standalone
`vue-tsc --noEmit`, persisted-lock dependency installation and the full offline
`npm ci` including install hooks. Malformed parsing and real self-import/constant
loop enforcement fixtures passed; the inspector static build passed. Effective
rule comparison found no enabled baseline rule with reduced severity. This reused
workflow compares its pinned historical ESLint8 base, not a fresh checkout of the
source base `cdd9147`; its candidate evidence binds to the exact source head above.

Corrected-head [avatar run41288204852](https://github.com/patchwerks/furbomek/actions/runs/41288204852)
also passed the existing offline test/browser suite. No additional source change
is made in this evidence update. Exact final PR-head verification and independent
review remain required before merge; no merge or deployment is performed here.
