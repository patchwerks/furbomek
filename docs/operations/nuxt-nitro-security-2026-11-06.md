---
created: 2026-11-06T01:29:40Z
branch: codex/13-nuxt-nitro-security
author: Codex
status: active
---
# Nuxt/Nitro security patch candidate

**Proposed, not qualified:** issue [13](https://github.com/patchwerks/furbomek/issues/13) has a bounded Nuxt 4.6.3 → 4.6.4 patch candidate, targeting Nitro 2.13.6 through ordinary supported resolution. The accepted comparison revision is `c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c`. Application source, configuration, server and viewer manifests/locks, and accepted CI helpers are unchanged. No override, forced peer resolution or unrelated direct upgrade is permitted.

Official [Nuxt 4.6.4 release notes](https://github.com/nuxt/nuxt/releases/tag/v4.6.4) and [Nitro 2.13.6 release notes](https://github.com/nitrojs/nitro/releases/tag/v2.13.6) describe additional security fixes and changed production error detail, dev-host checks, workspace detection and route rules. These upstream statements motivate qualification; they do not establish application reachability or runtime compatibility.

## Proposed qualification and provenance

The advisory [workflow](../../.github/workflows/nuxt13-qualification.yml) records the actual checked-out candidate SHA and accepted baseline SHA. It uses the accepted dependency proxy and digest-pinned Node 22.22.3 / 26.7.0 images, credential-free disposable workers and an isolated network. Networked provisioning disables scripts, audit and funding. Candidate code, dependency lifecycle hooks and configuration execute only in separate network-none workers. The trusted exporter admits bounded regular JSON/text/log files; artifacts are evidence, never execution authority.

An initial branch push may generate a lock from the stale accepted lock without a product PR. Resolution first attempts a minimal package-lock-only update. Solver failure or unrelated direct-version churn triggers the accepted fresh-pinned-directs method: temporarily pin every other direct dependency to its baseline installed version, resolve, restore the real manifest and resolve again. Every non-Nuxt direct installed version must remain exact; all independently resolved package URLs must use HTTPS npm registry URLs with SHA-512 integrity, and all Nuxt/Nitro occurrences must match 4.6.4/2.13.6. Unexpected later versions stop qualification. Every changed transitive package record is exported for review.

Generated-lock checks are exploratory. The coordinator must inspect one artifact, persist its exact bytes, and rerun both Node variants on that same published head before claiming persisted-lock qualification. `lock-mode.txt`, `comparison.json`, `package-lock.json` and SHA provenance distinguish these stages. Different generated locks across Node versions are not interchangeable evidence.

Both baseline and candidate require Nuxt prepare/build, TypeScript checks and the complete offline root npm lifecycle including the nested server install. Whole-repository and app ESLint JSON must parse without fatal errors, with no increased diagnostic totals or changes to enabled baseline rules. Malformed Vue/TypeScript fixtures must fail parsing; self-import and constant-loop negative controls remain errors. Dependency-tree validity and advisory npm-audit summaries are recorded. The separate [viewer workflow](../../.github/workflows/extension-viewer.yml) preserves actual compilation, type negative controls, unit checks and Chromium/Firefox browser checks while narrowly admitting this root dependency patch.

## Current evidence and remaining gates

Only source/data and syntax inspection is available at authoring time. No lock has yet been accepted, no hosted candidate results are asserted, and missing/failed checks remain missing/failed. Exact persisted-head hosted qualification, artifact review, independent contributor review and normal required checks remain pending. No merge or deployment is implied.

This is partial security progress, not complete remediation: NFT still constrains glob below the patched major; readdir-glob and lint parents still constrain affected minimatch versions. Deepmerge retains its prior narrowly scoped disposition, with no new risk acceptance. Advisory audit differences do not close issue 13 or dismiss provider alerts. No provider, media, robot, firmware or live deployment qualification is included.

Rollback is a reviewed revert of this bounded manifest/lock/workflow series to the accepted baseline. It is not a claim about a deployed runtime, and reintroduces the older dependency versions and their known limits.

## Changelog

- 2026-11-06: Corrected the creation timestamp to observed file creation and narrowed lock provenance admission for the accepted bundled `node_modules/@parcel/watcher-wasm/node_modules/napi-wasm` record. This exact child and its `@parcel/watcher-wasm` parent must both remain deep-identical to the accepted lock; the parent still passes the normal registry URL/integrity checks. The child is covered by that parent archive and has no separate URL/integrity in the accepted lock. No other provenance-free or new bundled record is exempt.
- 2026-11-06: Added exact 4.6.4 admission for every root/nested `nuxt`, `@nuxt/schema`, `@nuxt/nitro-server` and `@nuxt/vite-server` occurrence. Optional webpack/rspack builders are absent at baseline and rejected if newly introduced. This verifies affected package-family versions without forcing unrelated `@nuxt/kit` changes.
