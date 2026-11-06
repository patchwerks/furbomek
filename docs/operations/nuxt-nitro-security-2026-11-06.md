---
created: 2026-11-06T01:29:40Z
branch: codex/13-nuxt-nitro-security
author: Codex
status: active
---
# Nuxt/Nitro security patch candidate

**Refreshed source qualified after one unchanged viewer retry; final documentation-head checks and independent acceptance pending:** issue [13](https://github.com/patchwerks/furbomek/issues/13) has a bounded Nuxt 4.6.3 → 4.6.4 patch candidate, targeting Nitro 2.13.6 through ordinary supported resolution. The refreshed accepted comparison revision is `6d829351c305a56fb8104469446ae574a07dec7b`; earlier run records below retain their original baseline. Application source, configuration, server and viewer manifests/locks, and accepted CI helpers are unchanged. No override, forced peer resolution or unrelated direct upgrade is permitted.

Official [Nuxt 4.6.4 release notes](https://github.com/nuxt/nuxt/releases/tag/v4.6.4) and [Nitro 2.13.6 release notes](https://github.com/nitrojs/nitro/releases/tag/v2.13.6) describe additional security fixes and changed production error detail, dev-host checks, workspace detection and route rules. These upstream statements motivate qualification; they do not establish application reachability or runtime compatibility.

## Advisory scope and compatibility assessment

**Observed at accepted baseline:** the eight Nuxt advisories affect the installed `nuxt`, `@nuxt/schema`, `@nuxt/nitro-server` and `@nuxt/vite-server` family, with optional webpack/rspack builders absent. Qualification requires every installed occurrence of the affected family at 4.6.4 and `nitropack` at 2.13.6; it rejects introducing the absent alternate builders. Package presence and an affected version do not establish a demonstrated attack path.

| Official advisory | Relevant prerequisite or behavior change |
|---|---|
| [Nuxt workspace detection](https://github.com/nuxt/nuxt/security/advisories/GHSA-mjrq-cffv-q4qc) | `@nuxt/schema`: parent lock/settings files no longer widen the implicit workspace root. This is a real compatibility consideration for root and nested viewer resolution. |
| [Nuxt encoded-slash route matching](https://github.com/nuxt/nuxt/security/advisories/GHSA-f3x9-2chm-73c8) | `nuxt`, Nitro-server and Vite-server: catch-all/multi-segment pages combined with protective route rules. |
| [Nuxt development Host validation](https://github.com/nuxt/nuxt/security/advisories/GHSA-x2wv-5868-p7v2) | Webpack/rspack dev builders; default Vite is unaffected. Do not weaken host validation to accommodate testing. |
| [Nuxt payload/early404 handling](https://github.com/nuxt/nuxt/security/advisories/GHSA-r9jc-w898-3fv6) | SSR payload extraction with cache/SWR/ISR or experimental early404. |
| [Nuxt production error redaction](https://github.com/nuxt/nuxt/security/advisories/GHSA-96x6-fvhx-49hg) | Unexpected server-render errors lose message/data; deliberate HTTP errors remain client-visible. |
| [Nuxt Vite-server wildcard redirects](https://github.com/nuxt/nuxt/security/advisories/GHSA-p4h3-4h99-9665) | Experimental Vite server builder and wildcard redirect rules; ordinary Vite client bundling is a different surface. |
| [Nuxt island prop encoding](https://github.com/nuxt/nuxt/security/advisories/GHSA-hf59-9xwc-2g4p) | `nuxt`/Nitro-server: islands with attacker-influenced string props and cache/prerender conditions. Static generation is not a universal exclusion. |
| [Nuxt leading-double-slash normalization](https://github.com/nuxt/nuxt/security/advisories/GHSA-r99w-jh2x-3mg9) | Nitro-server page resolution versus path-scoped rules/middleware. |
| [Nitro cache hardening](https://github.com/nitrojs/nitro/security/advisories/GHSA-39r7-wfcx-99xg) | Cached handlers or cache/SWR/ISR rules: skip non-GET/HEAD and Range requests; avoid storing Set-Cookie, private/no-store/no-cache or unsupported Vary responses. |
| [Nitro wildcard proxy scope](https://github.com/nitrojs/nitro/security/advisories/GHSA-rhhp-7488-3qwf) | Wildcard proxy targets with a non-root prefix used as a boundary; final-target validation also changes wildcard redirects. |
| [Nitro wildcard redirects](https://github.com/nitrojs/nitro/security/advisories/GHSA-pqxc-r4h5-jc95) | Runtime wildcard redirects targeting exactly `/**`; platform-generated redirects have separate semantics. |

Both authored Nuxt configs use `srcDir: '.'`, `ssr: false`, disabled DevTools and strict type checking. No authored cache/proxy/redirect route rules, cached handlers, relevant page protections, islands, alternate server builders, explicit workspaceDir or custom dev host configuration were found in the accepted tracked source. This narrows known prerequisites; it does **not** prove non-exposure. Module-generated configuration, startup arguments, surrounding workspace files, deployed revisions and external routing remain unestablished. `ssr: false` does not prove that the root production Nitro server is absent. The viewer workflow generates a static site; its procedural renderer named `proxy.mjs` is not an HTTP proxy.

Workspace detection deserves normal root prepare/build/type and standalone viewer generation/type/browser checks in the clean accepted layout, because the viewer imports shared preview code and uses root dependencies. Do not add explicit workspaceDir without an observed resolution regression. The existing root/UI and viewer checks are the bounded compatibility gate; if effective generated route rules emerge, inspect those before deciding on a targeted test. No unconfigured feature, exploit fixture, tunnel or new service is introduced for this assessment.

The separate Express TTS proxy forwards fixed provider URLs and raw error messages. Nuxt renderer error redaction and Nitro proxy-scope fixes do not repair that service or qualify its provider behavior. The eleven upstream advisories are also distinct from the remaining glob/minimatch/deepmerge provider-alert inventory. This assessment supports the patch candidate, not an all-alerts-resolved claim.

## Proposed qualification and provenance

The advisory [workflow](../../.github/workflows/nuxt13-qualification.yml) records the actual checked-out candidate SHA and accepted baseline SHA. It uses the accepted dependency proxy and digest-pinned Node 22.22.3 / 26.7.0 images, credential-free disposable workers and an isolated network. Networked provisioning disables scripts, audit and funding. Candidate code, dependency lifecycle hooks and configuration execute only in separate network-none workers. The trusted exporter admits bounded regular JSON/text/log files; artifacts are evidence, never execution authority.

The initial published source `4ae2e6596cd399abe7ca9f6ceba2194da4c081a4` used a branch-push bootstrap trigger to generate a lock from the stale accepted lock without a product PR. The persisted-stage workflow removes that push trigger: pull requests must report exact `persisted` lock mode before passing, while manual workflow dispatch can still record exploratory resolution. Resolution first attempts a minimal package-lock-only update. Solver failure or unrelated direct-version churn triggers the accepted fresh-pinned-directs method: temporarily pin every other direct dependency to its baseline installed version, resolve, restore the real manifest and resolve again. Every non-Nuxt direct installed version must remain exact; all independently resolved package URLs must use HTTPS npm registry URLs with SHA-512 integrity, and all Nuxt/Nitro occurrences must match 4.6.4/2.13.6. Unexpected later versions stop qualification. Every changed transitive package record is exported for review.

Generated-lock checks are exploratory. The coordinator must inspect one artifact, persist its exact bytes, and rerun both Node variants on that same published head before claiming persisted-lock qualification. `lock-mode.txt`, `comparison.json`, `package-lock.json` and SHA provenance distinguish these stages. Different generated locks across Node versions are not interchangeable evidence.

Both baseline and candidate require Nuxt prepare/build, TypeScript checks and the complete offline root npm lifecycle including the nested server install. Whole-repository and app ESLint JSON must parse without fatal errors, with no increased diagnostic totals or changes to enabled baseline rules. Malformed Vue/TypeScript fixtures must fail parsing; self-import and constant-loop negative controls remain errors. Dependency-tree validity and advisory npm-audit summaries are recorded. The separate [viewer workflow](../../.github/workflows/extension-viewer.yml) preserves actual compilation, type negative controls, unit checks and Chromium/Firefox browser checks while narrowly admitting this root dependency patch.

## Current evidence and remaining gates

**Observed first hosted run:** [42144626039](https://github.com/patchwerks/furbomek/actions/runs/42144626039) succeeded on exact source `4ae2e6596cd399abe7ca9f6ceba2194da4c081a4`, against accepted baseline `c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c`, on Node 22.22.3/npm 10.9.8 and Node 26.7.0/npm 11.19.0. Both used `minimal-lock-update` with `persistedLockQualification:false`; neither needed fallback resolution. These results qualify the internally resolved candidates, not a checked-in lock or the separate viewer.

Both baseline and candidate passed normal root prepare/build/types and full offline npm ci/postinstall including the nested server install. App and whole-repository lint each remained at zero errors and warnings; malformed Vue/TypeScript parser controls failed as intended, self-import/constant-loop controls remained enforced, and enabled baseline rules were unchanged. Dependency trees reported no problems and the inspector static build passed. Normal builds produced Nitro `node-server` output. Node 26/npm 11 emitted an esbuild install-script policy warning in both variants; success is not proof that every dependency hook executed identically across npm versions.

The coordinator independently verified official artifact ZIP hashes, bounded inventories, extracted bytes and source/baseline identities before selecting the lock:

| Artifact | Official ZIP SHA-256 | Generated lock SHA-256 |
|---|---|---|
| [Node 22 / 13470090574](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13470090574) | `81f982a10c67f38b2d4f964c1ab5090442a84f5207e01a5743bf69133d77f9ab` | `8910233402c84add01ad3237ab470115fad6b68ab5bac1d2f891b99df91f57f5` |
| [Node 26 / 13470045712](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13470045712) | `1ca6cfbc81e9681ac8928d1ef66eee7f70344229381caaaba418acd073a9b1d6` | `8fcda3cd6ef3b23dc4aad02e18a5be400d3697cea981d688bb29e536635f4ef0` |

The exact Node 26 artifact lock is now persisted as the candidate `package-lock.json`, preserving its optional-binding libc metadata. The generated locks differ only in libc fields on 33 optional binding entries; versions, URLs, integrity and other record fields match. They are not byte-identical. Node 26 has 99 changed full package records relative to baseline; Node 22 has 119, including 20 additional metadata changes. All 14 non-Nuxt direct versions and their manifest ranges remain fixed. Both generated graphs contain the affected Nuxt family at 4.6.4, Nitro 2.13.6 and NFT 1.11.1, with the old archiver-utils glob/minimatch branch removed.

Both npm audit responses contain 28 baseline package findings (25 moderate, 3 low) versus 27 candidate package findings (20 moderate, 7 low). These include propagated dependency findings, not distinct advisory or GitHub alert counts. The same three direct advisory identities remain: glob GHSA-3g3m-2fjr-6pw4, minimatch GHSA-g3hv-75wg-m249 and deepmerge GHSA-gcqx-w48m-w2h4. The changed totals do not establish new direct advisories or complete remediation.

### Persisted-source qualification

This historical qualification used accepted baseline/enforcement `c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c`. Its artifact identities and results are unchanged by the refresh; they do not qualify the accepted builder/metadata additions combined with the security patch.

**Observed at exact source `fe95b52b7af9fff34cb429da151d713c0e3cd6f1`:** [Nuxt/Nitro run 42145701660](https://github.com/patchwerks/furbomek/actions/runs/42145701660) succeeded on both Node 22.22.3 and 26.7.0. The coordinator independently verified the official artifact digests, source/baseline identities, exact `persisted` mode and the same checked-in lock SHA-256 `8fcda3cd6ef3b23dc4aad02e18a5be400d3697cea981d688bb29e536635f4ef0` in both artifacts. This is qualification of the selected persisted lock, distinct from the earlier ephemeral resolution.

Both runtimes passed baseline/candidate normal prepare/build/types, the complete offline root lifecycle including nested server installation, valid dependency trees, malformed Vue/TypeScript parser controls, self-import/constant-loop enforcement and inspector build. App/repository lint remained zero errors and warnings, with enabled effective rules unchanged. The coordinator verified all 12 reported source checks successful, including [non-live verification 42145701684](https://github.com/patchwerks/furbomek/actions/runs/42145701684) and [CodeQL 42145698034](https://github.com/patchwerks/furbomek/actions/runs/42145698034). These results bind to the source SHA above, not a subsequent documentation revision.

| Persisted root artifact | Official ZIP SHA-256 |
|---|---|
| [Node 22 / 13470510733](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13470510733) | `34ad7dd2bf726741b12005f4714bd4c8ee2ba8ff0e9237944f5c0e4ba63a1bc3` |
| [Node 26 / 13470231491](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13470231491) | `816c662d4f4bea442d85134b72d81044044a4f05028aab4b8286d402ee18bff8` |

[Viewer run 42145701686](https://github.com/patchwerks/furbomek/actions/runs/42145701686) also succeeded at the same source. Both runtimes passed actual prepare, type checking, static generation and 62/62 unit tests with no failures/skips. The injected draw mutation failed at `app.vue(32,34)` with TS2339, and the restored source passed. Generation reported Nuxt 4.6.4 / Nitro 2.13.6 with the static preset and three generated routes. Client chunk-size warnings remain; client-rendered HTML under `ssr:false` is not server-rendered prerender content.

Chromium 156.0.8078.4 and Firefox 157.0 each passed all 31 browser cases on both Node versions, including keyboard/mobile, rendered cues, WebGL loss/unavailability, reduced motion and malformed/stale import handling. All four results have empty outbound-request and error arrays and no renderer failure. The hosted renderers were SwiftShader and llvmpipe; this does not qualify physical graphics hardware. The coordinator visually inspected Node 26 Chromium desktop-light and Node 22 Firefox desktop-dark/mobile PNGs: layout, text, procedural proxy and cue presentation were clear, with no correction required. This visual inspection is limited to those selected screenshots.

| Viewer artifact, including PNG evidence | Official ZIP SHA-256 |
|---|---|
| [Node 22 / 13469907655](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13469907655) | `07d430fd4435aa473b563684d5d1256be27488f8dd85e06edc8302a0dac27cdd` |
| [Node 26 / 13470310927](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13470310927) | `d9b1fa2d5cf0c4cb8ce5bae170dd0f022900cf13cabf435326c4958e6601a92a` |

Official artifact identity, digest and nonexpiry were checked before bounded inspection/extraction of regular allowlisted files; extracted candidate/enforcement SHA records matched the expected source and accepted baseline. No downloaded artifact code was executed. The metadata/log and PNG artifacts support the reported checks and selected visual inspection, not deployment authority.

**Still pending:** checks for the final documentation-only child and independent exact-head acceptance of [PR 50](https://github.com/patchwerks/furbomek/pull/50). Source qualification does not close issue 13, resolve all advisories, merge the PR or authorize deployment. No alert dismissal or new security risk acceptance is implied.

This is partial security progress, not complete remediation: NFT still constrains glob below the patched major; readdir-glob and lint parents still constrain affected minimatch versions. Deepmerge retains its prior narrowly scoped disposition, with no new risk acceptance. Advisory audit differences do not close issue 13 or dismiss provider alerts. No provider, media, robot, firmware or live deployment qualification is included.

Rollback is a reviewed revert of this bounded manifest/lock/workflow series to the accepted baseline. It is not a claim about a deployed runtime, and reintroduces the older dependency versions and their known limits.

## Changelog

- 2026-11-06: Corrected the creation timestamp to observed file creation and narrowed lock provenance admission for the accepted bundled `node_modules/@parcel/watcher-wasm/node_modules/napi-wasm` record. This exact child and its `@parcel/watcher-wasm` parent must both remain deep-identical to the accepted lock; the parent still passes the normal registry URL/integrity checks. The child is covered by that parent archive and has no separate URL/integrity in the accepted lock. No other provenance-free or new bundled record is exempt.
- 2026-11-06: Added exact 4.6.4 admission for every root/nested `nuxt`, `@nuxt/schema`, `@nuxt/nitro-server` and `@nuxt/vite-server` occurrence. Optional webpack/rspack builders are absent at baseline and rejected if newly introduced. This verifies affected package-family versions without forcing unrelated `@nuxt/kit` changes.
- 2026-11-06: Added primary advisory links for the eight Nuxt and three Nitro fixes, exact-source prerequisite limits, workspace compatibility requirements and the separate Express error boundary. Hosted results and persisted-lock acceptance remain pending.
- 2026-11-06: Removed the initial branch-push bootstrap trigger for the persisted stage and required exact persisted-lock mode for pull-request success; manual dispatch remains available for explicitly exploratory evidence. No run result is inferred from this workflow edit.
- 2026-11-06: Recorded successful first ephemeral qualification, verified artifact identities, exact selected Node 26 lock, metadata-only cross-runtime lock differences and honest audit residuals. Persisted-head and viewer qualification remain pending.
- 2026-11-06: Recorded successful persisted-source root/viewer/non-live/CodeQL checks at `fe95b52b7af9fff34cb429da151d713c0e3cd6f1`, verified artifact provenance and selected coordinator screenshot inspection. Final documentation-head checks and independent PR 50 acceptance remain pending.


## Accepted-main refresh preparation

**Observed preparation at 2026-11-06T04:09:16Z:** PR 50 was locally integrated with accepted main `6d829351c305a56fb8104469446ae574a07dec7b`, preserving the accepted PR 48 builder/metadata tooling and PR 49 README. Both the root advisory baseline and viewer enforcement pins now identify that exact accepted revision. The root comparison therefore includes the accepted builder/metadata source on both sides, with the same proposed security dependency patch. Historical run evidence above does not qualify this refreshed source.

The original PR 50 `package.json` and `package-lock.json` bytes are preserved from `3a16463d859e6331c7125b262d28c3621b2c6d35`; the lock SHA-256 remains `8fcda3cd6ef3b23dc4aad02e18a5be400d3697cea981d688bb29e536635f4ef0`. No dependency resolution was performed for this refresh. Nuxt 4.6.4, Nitro 2.13.6 and the 14 other direct installed versions remain fixed. Accepted application, builder, metadata, tests, README and other workflow bytes are preserved.

The viewer workflow retains accepted `builder.d.mts` admission, builder screenshot and lint artifact allowlists, root preparation and zero-warning targeted authoring lint. Its actual browser/CLI roundtrip and metadata integration tests remain unchanged; the separate metadata workflow remains byte-identical to accepted main. The only main-relative paths are the original six PR 50 files: root manifest/lock, two qualification workflows, PLAN and this record.

**Pending:** fresh root baseline/candidate qualification on both pinned Node runtimes, complete accepted viewer/builder/browser and metadata checks, other applicable exact-head checks, artifact inspection and independent review of the refreshed published head. Local preparation uses only static data/syntax and diff checks; no candidate installation, hook, build, test or configuration execution runs on the host. Merge, deployment, issue closure, advisory dismissal and new risk acceptance remain excluded.

### Refresh changelog

- 2026-11-06T04:09:16Z: Integrated accepted main and advanced both qualification pins while preserving the selected lock and accepted features; fresh execution and review remain pending.


## Refreshed source qualification

**Observed at 2026-11-06T04:25:34Z:** exact source `a4dfd3dd2358de69d084561156234c96fff80515` qualified against accepted baseline/enforcement `6d829351c305a56fb8104469446ae574a07dec7b`. The coordinator verified all 14 current source checks successful after the viewer reproduction below. This is new evidence for accepted builder/metadata tooling combined with the security patch; the earlier `fe95b52b7af9fff34cb429da151d713c0e3cd6f1` results retain their original `c0c3f7ce44cfa3db34cbe46a723bf1fc16b56b6c` baseline. Results do not transfer to a subsequent documentation head.

### Root and metadata checks

[Root run 42161228055](https://github.com/patchwerks/furbomek/actions/runs/42161228055) passed on Node 22.22.3/npm 10.9.8 and Node 26.7.0/npm 11.19.0. Both artifacts report exact `persisted` lock mode and SHA-256 `8fcda3cd6ef3b23dc4aad02e18a5be400d3697cea981d688bb29e536635f4ef0`, with all 14 non-Nuxt direct installed versions preserved. Baseline and candidate prepare/build/types and full offline root lifecycle passed, including actual root postinstall preparation/build and nested server installation. Node 26 npm reported an allowScripts warning blocking the esbuild dependency postinstall; successful root postinstall does not mean every dependency hook executed.

Both app/repository lint reports have zero errors, warnings and fatal errors. Malformed Vue/TypeScript controls each report one fatal parse error; self-import and constant-condition controls remain errors. Dependency trees have no problems, effective Vue/TypeScript rule-change arrays are empty, and inspector/comparison completed. ESLint is 10.14.0. Audit totals remain 28 baseline package findings (25 moderate, 3 low) versus 27 candidate findings (20 moderate, 7 low), with the same three residual advisory identities; this does not close remediation.

| Root artifact | Official ZIP SHA-256 |
|---|---|
| [Node 22 / 13477500356](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13477500356) | `6974be219743222febb6098cc5c7461ae32a2ea7c3ae1eb57a7cf1d9059e44f4` |
| [Node 26 / 13476692847](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13476692847) | `aa7182d1e64f0da8f6715724df68f00b085e5af7395ef83d226a6ac16fcc354b` |

The unchanged metadata workflow was manually dispatched at this exact source: [run 42161261516](https://github.com/patchwerks/furbomek/actions/runs/42161261516). Node 22.22.3 and 26.7.0 each actually passed 87/87 tests with zero failures, skips, cancellations or todo cases in offline workers. The workflow uploads no artifact; official run/job identities and inert logs provide the evidence, with no metadata artifact digest claimed.

### Viewer failure and unchanged reproduction

[Viewer run 42161227944, attempt 1](https://github.com/patchwerks/furbomek/actions/runs/42161227944/attempts/1) passed 66/66 unit tests, zero-warning targeted authoring lint, normal types, the injected `app.vue(35,34)` TS2339 negative control and restored-source types on both Node versions. Static generation passed with three routes. The client-rendered `ssr:false` content is not prerendered HTML; chunk-size/timing warnings remain.

Node 22 Chromium 156.0.8078.4 and Firefox 157.0 each passed all 43 browser cases. Node 26 Firefox also passed 43, but Node 26 Chromium failed: a 30-second timeout waiting for the keyboard-triggered `filechooser` at `browser-check.cjs:95:45`, called from line 356. The record contains 25 completed baseline cases and shows the file input focused, visible, with a solid three-pixel outline and document focus. It failed before builder cases. These observations do not establish the cause, and that failed configuration does not contain the successful outbound/pageerror arrays.

The coordinator reran only the failed job once, without source or test changes. [Attempt 2](https://github.com/patchwerks/furbomek/actions/runs/42161227944/attempts/2), Node 26 job `127709131795`, passed both browsers with all 43 cases, including the actual keyboard file import, builder download/reimport, CLI metadata roundtrip and exact-byte tamper rejection. It again passed 66/66 unit tests, zero lint diagnostics, the meaningful TS rejection/restoration and static generation. Node 22 results remain from attempt 1; they were not rerun. The first failure and logs are retained. Its cause remains unresolved: this successful unchanged reproduction is not a source fix or a demonstrated flake fix.

| Viewer attempt / artifact | Official ZIP SHA-256 |
|---|---|
| [Attempt 1 Node 22 / 13476727650](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13476727650) | `a5698f25c5fafca409e4deb22d645b420492c6d4f9b78db5ba63cf65481c2496` |
| [Attempt 1 Node 26, failed Chromium / 13476508386](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13476508386) | `0d11a67016a598542b74403c2700afd01b4bc41afe07640a2f12d5148da16c9e` |
| [Attempt 2 Node 26 / 13476479151](https://api.github.com/repos/patchwerks/furbomek/actions/artifacts/13476479151) | `f59b021c53d2b49fc06e73e9eb8ff1fa41b5a1ae4658ae7fbd0026f1bc1b753f` |

The new Node 26 artifact was created at `2026-11-06T04:22:12Z`; attempt-2 job upload logs bind its ID and digest despite its name matching the first-attempt artifact. Official run/source/repository identities, nonexpiry and ZIP hashes were checked before bounded extraction of unique allowlisted regular files (at most 8 MiB per file, 32 MiB per job and 40 files). Embedded candidate and enforcement identities match the exact source and accepted baseline above. Both first-attempt archives and failed logs remain preserved separately from retry evidence. No artifact code was executed on the host.

Successful browser records contain empty outbound-request and pageerror arrays. These arrays do not assert absence of all browser console messages; the previously accepted nonblocking CSP select-chevron console note remains a separate observation. The coordinator actually inspected attempt-1 Node 22 Chromium `builder-light.png`, Node 26 Firefox `builder-dark.png` and Node 22 Firefox `builder-mobile.png`; no visual correction was required. Visual acceptance is limited to those screenshots.

**Still pending:** fresh applicable checks for the final documentation head and independent exact-head review of PR 50. These source results do not close issue 13, establish complete security remediation, dismiss advisories, grant new risk acceptance, merge the PR or deploy any runtime.

### Qualification changelog

- 2026-11-06T04:25:34Z: Appended refreshed root and metadata evidence, both viewer attempts and verified artifact provenance; preserved the unresolved first-attempt keyboard timeout and distinguished successful unchanged reproduction from a fix. Recorded bounded coordinator screenshot inspection; final documentation-head checks and independent review remain pending.
