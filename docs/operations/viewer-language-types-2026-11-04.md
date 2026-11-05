---
created: 2026-11-04T10:42:45Z
branch: codex/32-viewer-language-types
author: patchWERKS / Codex
status: active
---
# Viewer language and script typechecking

**Candidate; preparation was source-only, followed by hosted qualification below.** This owner-authorized follow-up to PR 42
belongs to [issue 32](https://github.com/patchwerks/furbomek/issues/32), under
[claim 6628618250](https://github.com/patchwerks/furbomek/issues/32#issuecomment-6628618250).
Preparation starts from accepted main `95a9a8821d4ff245399a4f8d425742222ef787a1`.

The English viewer sets `app.head.htmlAttrs.lang` to `en`; the existing real
Chromium/Firefox browser suite now reads the rendered HTML element's language.
`app.vue` uses `script setup lang="ts"`, strict compiler settings, typed DOM refs,
events and lifecycle handles. DOM target and mount guards account for nullable
browser elements. Parse results remain unmodified shallow refs; no cloning,
proxying, timeline changes or new renderer behavior is introduced.

`packages/extension-preview/index.d.mts` describes the existing immutable parser
and sampler contract. Its private unique symbol prevents consumers constructing
a parsed pack structurally; the existing runtime WeakSet remains the actual
validation authority. `proxy.d.mts` describes only the existing renderer handle.
These module-specific declarations do not check the JavaScript implementations;
they require source correspondence review and do not qualify the core or renderer
internals as TypeScript-checked. Neither module's runtime bytes nor schema changed.

## Required disposable-worker evidence

The existing credential-free offline compiler phase runs the unchanged command:

```sh
./node_modules/.bin/vue-tsc --noEmit -p apps/extension-viewer/tsconfig.json
```

It must pass normal source first. The next step runs
`tests/typecheck-negative-control.mjs` only from `/scratch/source`, injecting
`const n = 1; n.foo.bar();` into `draw` in that disposable copy. The identical
checker must terminate normally with status 2 and exactly one TypeScript error:
`app.vue` TS2339 for property `foo` on a number. The script restores the exact
original bytes in `finally`, then requires the same checker to succeed again.
`types.log` and bounded `types-negative-control.log` preserve those outcomes.
No credentialed host candidate execution is part of this procedure.

The existing two Node versions and two real browsers retain all previous cases;
`document-language` adds one case per browser. Normal static generation and
core/artifact regressions remain required. Source-only syntax and whitespace
inspection is preparation evidence, not execution evidence. At initial preparation, no hosted result,
artifact SHA or independent acceptance was claimed. The source qualification
below supersedes that execution checkpoint; independent acceptance remains pending.

## Limits and rollback

No dependency, core runtime, schema, procedural geometry, proxy behavior, legacy
root app, live service or physical device changes are authorized here. The workflow
change is confined to the offline compiler proof and exact declaration/log
allowlists. Independent workflow review and exact published-head checks remain
required before acceptance. Rollback reverts this bounded source change; it does
not affect installed software or hardware. Issue 32 remains open.


## Observed hosted source qualification, 2026-11-04

[PR 46](https://github.com/patchwerks/furbomek/pull/46) source
`552cc5b849b0688c757e4acf7f6a0979b8d5d5c1` passed both jobs of
[run 41826988549](https://github.com/patchwerks/furbomek/actions/runs/41826988549),
completed at 12:12:40 UTC. This is the implementation plus the existing event
button's attribute-order correction. The worker's `candidate-sha.txt` records
that source in both artifacts; `enforcement-sha.txt` records
`cdd9147fac9141fa0c75b5058f9dce46c7885188`. The artifact name suffix is the PR
merge ref `ef229e2ed25126726413b67c2a5f554f56eee356`, not the tested source identity.
GitHub artifact metadata binds both archives to this run and the exact source SHA.

| Worker | Artifact ID | Downloaded archive SHA-256, matching GitHub metadata |
|---|---|---|
| Node 22.22.3 / npm 10.9.8 | 13319307696 | `8a070286830d5eefd5db1f59651818047e792f2683286fcf51c93dc80278f270` |
| Node 26.7.0 / npm 11.19.0 | 13318919503 | `7804d81e951215462e25e4b604e053fbc9d086db59914f3d3a3069196a0db104` |

**Observed in both workers:** normal `types.log` is empty and its mandatory
compiler step succeeded. `types-negative-control.log` contains exactly:

```text
Injected draw error
apps/extension-viewer/app.vue(32,34): error TS2339: Property 'foo' does not exist on type '1'.

Restored viewer source

PASS: baseline accepted; draw mutation rejected with app.vue TS2339; restored source accepted.
```

The checked source requires normal termination/status 2 and exactly that single
TypeScript diagnostic, restores original bytes in `finally`, then requires status
0 from the identical checker. This establishes that the viewer's script logic is
checked; it does not claim checking of JavaScript module internals.

Nuxt prepare and static generation passed under Nuxt 4.6.3, Vue 3.5.44 and
Vite 8.3.5 in each worker; output was generated at the standalone viewer's
`.output/public`. Logs retain the nonfatal large-chunk and plugin-timing warnings
and the expected `ssr: false` notice. Both `unit.log` records show 62 tests passed,
zero failures, cancellations, skips or todos.

All four real-browser records passed 31 cases: Chromium 156.0.8078.4 and
Firefox 157.0 on each Node version. Each includes `document-language`, whose
published test reads `page.locator('html').getAttribute('lang')` and asserts `en`.
All four report empty outbound-request and uncaught-error arrays. Existing
playback, import, reduced-motion, teardown and keyboard cases remain present.
The published source assertion plus the passing browser case is the language
proof; this is not a claim that the JSON record independently stores its value.

Archives were inspected as inert bounded ZIP entries and text/JSON only, with
archive hashes, paths, entry sizes and aggregate size checked before reading.
No downloaded source or artifact code ran on the publishing host, and no new
visual acceptance is claimed. This evidence applies only to the source SHA above.
The documentation child still requires applicable exact-head checks and independent
PR 46 acceptance; issue 32 remains open.

## Changelog

- 2026-11-04: Recorded exact-source hosted typecheck negative-control, static,
  62-test and four-way 31-case browser evidence with matching archive digests;
  retained final-head and independent-acceptance gates.
