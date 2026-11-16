---
created: 2026-11-06T10:50:18Z
branch: codex/32-browser-metadata
author: patchWERKS / Codex
status: active
---
# Browser companion validation qualification

**Source qualified; final-head checks and independent review pending.** This bounded
[issue 32](https://github.com/patchwerks/furbomek/issues/32) slice starts from
accepted main `63184419ab5c5437ffc37028ba7829ae53c4f289`. It adds browser byte
validation and tests, without UI wiring or importing pending PR 51/52 changes.

The [API contract](../contributing/presentation-metadata.md#browser-byte-validation-candidate-2026-11-06)
returns an immutable branded core pack, immutable strict companion and exact-byte
SHA-256 digest. Both inputs are bounded and copied synchronously; shared byte
buffers are rejected. Native Web Crypto errors fail closed with a fixed message.
The accepted core parser, companion format, files/CLI, dependencies, lockfiles
and production viewer remain unchanged.

## Evidence and pending gates

Observed locally: static JavaScript syntax checks only, on `browser.mjs`,
`tests/browser.test.mjs` and `tests/browser-check.cjs`; workflow YAML parsing,
extracted Bash syntax and whitespace checks also passed. This is not test execution.
Candidate code, installs, builds and tests must run only in credential-free
hosted disposable workers. No local runtime pass is claimed.

The existing metadata workflow's test wildcard includes the seven new wrapper
tests on both pinned Node versions, with experimental VM modules already enabled.
The viewer workflow invokes the standalone native-browser harness after its
existing viewer runner in each network-none worker. Its fixed loopback server
serves only one inert HTML document and the three exact module URLs; no arbitrary
filesystem URL mapping or remote request is allowed. A restrictive CSP and request
allowlist apply. Ten separate browser cases cover known-answer native hashing,
core branding/freezing, exact-byte tampering, identity mismatches, malformed
inputs, unsupported versions, bounds, offset views, in-flight caller mutation,
digest failure and inert input text (some cases group multiple assertions).

`browser-metadata-results.json` is bounded to 16 KiB by the harness and is added
to the existing artifact allowlist. Existing 43-case viewer checks, 66 unit checks,
source SHA evidence, provisioning, locks, dependency admission and enforcement
baseline `6d829351c305a56fb8104469446ae574a07dec7b` are preserved. The hosted
source results below supersede the preparation-only runtime status. Independent
review and final documentation-head checks remain required. The exported declaration
is not consumed by the existing viewer typecheck; its types are statically
reviewed but not independently compiler-qualified by that check.

## Scope and rollback

Remove the browser module/declaration/tests and the two workflow additions to
revert this slice. No persisted state migration exists. This work does not grant
authorship, media rights, installation, execution, deployment, live/provider,
Hermes, OBS or physical-device authority. Issue 32 remains open; no merge or
release is claimed.


## Observed source qualification — 2026-11-06T10:57:06Z

[PR 53](https://github.com/patchwerks/furbomek/pull/53) source
`7350419b5585a6379d90c84d3a7f658352536e61` passed all 14 source checks.
Evidence applies to this exact revision; it does not qualify a subsequent
documentation head automatically.

[Metadata run 42205915021](https://github.com/patchwerks/furbomek/actions/runs/42205915021)
passed 94/94 tests on each of Node 22.22.3 and 26.7.0, with zero failures,
cancellations, skips or TODOs. The count is 59 existing core tests, 28 existing
metadata tests and seven new browser-wrapper tests. Official logs individually
confirm native Web Crypto known-answer hashing and immutable branding, identity
and exact-byte mismatch rejection, strict parsing before digest invocation,
offset views and caller mutation during an in-flight digest, shared-buffer
rejection, isolated-context missing/insecure/rejecting Web Crypto failures, and
the fixed browser dependency graph with input retained as data.

[Viewer run 42205915244](https://github.com/patchwerks/furbomek/actions/runs/42205915244),
attempt 1, passed both Node jobs against enforcement revision
`6d829351c305a56fb8104469446ae574a07dec7b`:

| Build runtime | npm | Existing viewer units | Existing viewer cases per browser | Separate metadata cases per browser |
| --- | --- | --- | --- | --- |
| Node 22.22.3 | 10.9.8 | 66/66 | 43/43 | 10/10 |
| Node 26.7.0 | 11.19.0 | 66/66 | 43/43 | 10/10 |

Each job qualified Chromium 156.0.8078.4 and Firefox 157.0. All four browser
configurations passed the existing viewer scenarios and the ten separate native
metadata cases; these remain distinct suites. Both jobs passed targeted lint
with zero errors/warnings, normal typechecking, the negative control and restored
typecheck, and static generation. The declaration limitation above still applies.

The coordinator independently verified official artifact ZIP hashes, exact
source/enforcement records, bounded regular-file inventories (41 files per
artifact), all four viewer records and all four metadata records. Viewer outbound
and error arrays were empty; metadata blocked-request and error arrays were empty.
This does not claim console or CSP-violation absence: the existing viewer harness
does not collect that evidence. No screenshot re-review was performed because
this slice changes no UI.

| Artifact | GitHub artifact ID | Verified ZIP SHA-256 |
| --- | --- | --- |
| Node 22 viewer qualification | `13496138426` | `a9a049b738ed361519345464098eecc71446a1bb52e5f53eb56166acb9200a03` |
| Node 26 viewer qualification | `13496248941` | `e320265258641218b85e6902a6cf8d64a3cf3a37f68f80b3dc8a89ef9783ebf9` |

Supporting source checks also passed:
[starter examples 42205914944](https://github.com/patchwerks/furbomek/actions/runs/42205914944),
[non-live verification 42205915015](https://github.com/patchwerks/furbomek/actions/runs/42205915015),
and [CodeQL 42205910120](https://github.com/patchwerks/furbomek/actions/runs/42205910120).
Local evidence custody includes `metadata-source/verified-summary.json`,
`viewer-source/validation-summary.json` and `viewer-source/root-verification.json`
under the coordinator's `browser-metadata32-20261106` output directory. These
reports support the linked official records; local paths are not acceptance gates.

Final documentation-head checks and independent PR review remain pending.
There is no UI wiring, schema or dependency change, new storage/network authority,
authenticated author identity, rights approval, merge, deployment or live action.

## Changelog

- 2026-11-06T10:57:06Z: Recorded exact-source Node and four-configuration browser
  qualification, verified artifact hashes and existing-suite preservation;
  retained declaration limits, final-head checks and independent acceptance gates.
