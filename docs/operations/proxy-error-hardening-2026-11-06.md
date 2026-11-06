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

## Source qualification, 2026-11-06T10:56:23Z

**Observed:** source `0f9dc6b4dd77a45558265ea5212c846550a23fe5` passed
[proxy run 42206046796, attempt 1](https://github.com/patchwerks/furbomek/actions/runs/42206046796/attempts/1).
Node 22.22.3 / npm 10.9.8 and Node 26.7.0 / npm 11.19.0 each passed 85/85 tests:
all 13 existing regressions plus 72 additions, with zero failures, cancellations,
skips or TODOs. The exact passing test-name sets match across Node 22's TAP and
Node 26's spec output. Both syntax logs are empty successful results. The first
attempt passed; no retry or corrective runtime patch was needed.

Passing cases include early audio failure returning fixed JSON; late failure
terminating incomplete bytes without JSON; cancellation on normal and large
stream disconnect; cancellation when the client disconnects while fetch remains
pending; successful 2 MiB chunks under backpressure; staged-header failure
clearing provider headers; partial-content status/header preservation; and
same-process recovery. The route matrix covers transport and invalid/non-success
statuses on all five routes, malformed provider JSON on all metadata routes,
fixed parser errors and unknown middleware failure. These are actual proxy child
processes on private Unix sockets with synthetic provider responses.

Official downloaded ZIP digests matched the GitHub artifact metadata. Both
artifacts were unexpired at collection and contained exactly the six unique,
regular allowlisted files: `ci.log`, `unit.log`, `syntax.log`, `versions.txt`,
`candidate-sha.txt` and `enforcement-sha.txt`. No symlinks or duplicate entries
were admitted; each file was below 8 MiB and each job below 24 MiB. Embedded
source identity matched the source above; enforcement identity matched accepted
`63184419ab5c5437ffc37028ba7829ae53c4f289`. Artifact names contain GitHub's PR
merge-context SHA; the checked `candidate-sha.txt` binds the actual source head.

| Runtime | Official artifact ID | ZIP SHA-256 | Total uncompressed evidence bytes |
|---|---|---|---|
| Node 22.22.3 | 13496088533 | `9eeb26a21277ee86cdb5f8c2d699fb2eb3f3617a48b8e48b70ca757f0e76f7bb` | 15,785 |
| Node 26.7.0 | 13495879268 | `d7abd744e8d099f461bcf6e1161bcf557faaf71d4f432a2dbe1a0ad0446f09ca` | 6,583 |

The coordinator independently checked these artifacts, identities, bounds and
actual counts. All ten source-head PR 54 checks succeeded, including
[non-live verification 42206046667](https://github.com/patchwerks/furbomek/actions/runs/42206046667)
and [CodeQL 42206042705](https://github.com/patchwerks/furbomek/actions/runs/42206042705).
Local retained evidence is under
`outputs/proxy13-hardening-20261106/source-evidence/` in the parent workspace:
official run/jobs/artifact metadata, original ZIPs, official run logs, validated
extracted evidence and `verification.json`. It is not added to product source.

This supersedes the preparation-time pending runtime statement above only for
this exact source. The documentation follow-up changes only this record and
PLAN; application, test, dependency and workflow bytes remain the qualified
source bytes. Final documentation-head checks and independent PR 54 acceptance
remain pending. The offline, credential-free worker boundary and synthetic
upstream limitation still apply. No real provider, deployed service, production
security, robot/device, Hermes, OBS or public-stream qualification is implied;
no merge or deployment was performed.

### Qualification changelog

- 2026-11-06T10:56:23Z (codex/13-proxy-error-hardening): Appended verified
  first-attempt source qualification, artifact provenance and remaining final-head
  and independent acceptance gates; preserved original preparation history.
