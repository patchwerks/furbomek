---
created: 2026-11-06T10:50:48Z
branch: codex/13-proxy-error-hardening
author: Codex
status: active
---
# Bounded proxy error hardening

Candidate for [issue 13](https://github.com/patchwerks/furbomek/issues/13),
based on accepted `63184419ab5c5437ffc37028ba7829ae53c4f289`.
This is source preparation, not deployment or complete production security.

## Contract

All five fixed proxy routes return `{ "error": "Upstream service request failed." }`
for caught transport/protocol/JSON failures with HTTP 502. Provider 400–599
responses retain their status with that same local JSON; their bodies are
cancelled without parsing, and their headers are not forwarded. Invalid,
non-integer, informational and unhandled redirect statuses fail closed as 502.
Successful metadata JSON remains unchanged, including any provider-defined fields.

Successful audio retains bytes, status and provider headers. The reader pump
waits for its first read before staging headers, observes response backpressure,
and cancels its reader on client disconnect, including a client that disconnected
while fetch was pending. Errors before headers are sent return the fixed 502;
after headers, the incomplete response is destroyed without appending JSON.
Staged provider headers are removed if header setup fails. Raw stream-error
logging is removed. Normal listener/startup, CORS, provider URLs and auth
forwarding remain unchanged.

Express parser errors use fixed local messages for invalid JSON (400), oversized
bodies (413), unsupported charset/encoding (415), aborted bodies (400) and invalid
body size (400). Unknown middleware errors return generic HTTP 500. Error objects,
payloads, tokens, paths and stacks are neither serialized nor logged.

This does not add authentication, binding restrictions, rate limits, retries,
timeouts, a new credential store or a general abort framework. Successful provider
content is not blanket-sanitized. The prototype's broader security limitations
remain; this work does not qualify any provider, live service or physical system.

## Qualification and evidence

**Observed, static only:** changed JavaScript passed `node --check`; the new
workflow parsed as YAML and its embedded shell passed `bash -n`. No candidate
code, package installation, build or tests executed on the credentialed host.

**Pending:** Node 22.22.3 and 26.7.0 hosted qualification, exact-source artifact
inspection and independent acceptance. The new
[workflow](../../.github/workflows/proxy-error-qualification.yml) derives its
isolation from the accepted extension-viewer workflow: accepted server manifests
and locks must match byte-for-byte, accepted `tools/ci` must be unchanged, and
source indirection/environment configs are rejected. Only bounded server files
are staged. Networked provisioning uses the accepted dependency proxy and
`npm ci --prefix server --ignore-scripts`; no root install occurs. A separate
credential-free, offline UID 1000 worker runs the actual server tests and syntax
checks with read-only root, dropped capabilities, bounded temporary storage,
and no host home, socket or device mounts. Bounded inert evidence includes source
and enforcement SHAs. This workflow is advisory; independent acceptance is
required before merge.

The [test guide](../../server/TESTING.md) describes the real child-process Unix
socket harness, synthetic upstream failures and recovery controls. Existing 13
regressions remain. New fixtures exercise all routes, rejected status/body/header
handling, malformed provider JSON, parser errors, early/late stream failure,
partial-content success, staged-header failure, large-chunk backpressure and
client-disconnect cancellation. Tests use inert sentinel credentials only.
Runtime results must be appended with actual source/run identities; static
inspection must not be promoted into passing runtime evidence.

## Rollback and scope

Rollback restores `server/tts-proxy.js` from the accepted base; dependencies and
normal startup configuration are unchanged. The new tests and advisory workflow
are reviewable independently. No merge, deployment, provider calls, device,
Hermes, OBS, firmware or public-stream operations were performed.

## Changelog

- 2026-11-06T10:50:48Z: Prepared the bounded error contract, actual-process
  regressions and isolated advisory matrix; runtime qualification remains pending.
