---
created: 2026-11-06T10:50:18Z
branch: codex/32-browser-metadata
author: patchWERKS / Codex
status: active
---
# Browser companion validation preparation

**Proposed; runtime qualification pending.** This bounded
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
baseline `6d829351c305a56fb8104469446ae574a07dec7b` are preserved. Qualification
must still record exact source SHA, Node/browser versions and outcomes from both
Node jobs with Chromium 156 and Firefox 157. No hosted results exist for this
candidate yet. Independent review and exact-head checks remain required. The exported declaration
is not consumed by the existing viewer typecheck; its types are statically
reviewed but not independently compiler-qualified by that check.

## Scope and rollback

Remove the browser module/declaration/tests and the two workflow additions to
revert this slice. No persisted state migration exists. This work does not grant
authorship, media rights, installation, execution, deployment, live/provider,
Hermes, OBS or physical-device authority. Issue 32 remains open; no merge or
release is claimed.
