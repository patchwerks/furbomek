---
created: 2026-11-04T10:42:45Z
branch: codex/32-viewer-language-types
author: patchWERKS / Codex
status: active
---
# Viewer language and script typechecking

**Candidate, source inspected only.** This owner-authorized follow-up to PR 42
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
inspection is preparation evidence, not execution evidence. No hosted result,
artifact SHA or independent acceptance is claimed yet.

## Limits and rollback

No dependency, core runtime, schema, procedural geometry, proxy behavior, legacy
root app, live service or physical device changes are authorized here. The workflow
change is confined to the offline compiler proof and exact declaration/log
allowlists. Independent workflow review and exact published-head checks remain
required before acceptance. Rollback reverts this bounded source change; it does
not affect installed software or hardware. Issue 32 remains open.
