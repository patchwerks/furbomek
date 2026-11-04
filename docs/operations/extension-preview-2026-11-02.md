---
created: 2026-11-01T22:05:19Z
branch: codex/32-extension-contract
author: patchWERKS / Codex
status: active
---
# Extension preview first-slice candidate

Issue: [furbomek#32](https://github.com/patchwerks/furbomek/issues/32).
Accepted base: `cdd9147fac9141fa0c75b5058f9dce46c7885188` from canonical main.
The issue's earlier intake-only posture is historical; the owner subsequently
authorized this bounded data-only implementation. The issue and shared Project
retain task/claim status; this record describes the source boundary and evidence.

## Implemented source

`packages/extension-preview/` contains a private dependency-free ESM parser,
stateless sampler, separate Node file loader, JSON schema and synthetic fixture.
The browser core parses at most 1 MiB of strict UTF-8 JSON, rejects duplicate
decoded keys, limits nesting and event counts, enforces exact fields and declared
presentation capabilities, and freezes/brands accepted data. Sampling is derived
only from elapsed position with fixed cue expiry and neutral reset/end behavior.
The Node loader uses explicit operator paths, no-follow regular-file checks,
bounded reads and descriptor metadata checks. See the
[package contract](../../packages/extension-preview/README.md) for exact limits.

## Evidence and remaining acceptance

Source construction and inspection are not runtime proof. No candidate package,
dependency installer or test has been executed on the credentialed publishing
host. A separate test worker prepares adversarial tests and hosted disposable
Node 22/26 verification. Runtime results, exact candidate SHA and independent
review must be linked in the PR before acceptance; they are not claimed here.
Independent `pysol-dev` approval remains required. The parent coordinator owns claim,
issue and Project updates and final review.

No root workspace/dependency change, Nuxt connection, renderer, viewer, visual
asset, character-model license, voice, Hermes call, broker write, OBS operation,
robot access, deployment or installed runtime is delivered. No user imagery was
selected/generated, so this slice does not perform design or Photo Atlas work.
The wider extension/viewer milestone and existing safety/live qualification gates
remain open.

## Rollback

Before integration, discard this isolated candidate. After an accepted merge,
revert its package, dedicated verification and documentation changes together.
There is no installed service, migration, mutable runtime state or device write
to roll back. Do not alter unrelated accepted architecture or live configuration.

## Observed hosted evidence, 2026-11-02

Implementation revision: `6c43073d27ecf6ff035a65d04d767394a37efe00` in
[draft PR 41](https://github.com/patchwerks/furbomek/pull/41).
The pending statements above describe initial source preparation; the following
hosted results supersede that runtime-evidence status, not the independent-review
gate or the wider issue scope.

- [Extension checks 41355447251](https://github.com/patchwerks/furbomek/actions/runs/41355447251):
  Node 22 and Node 26 each passed **59/59 tests**, with zero failures, cancellations,
  skips or todos. Logs demonstrate parser/timeline adversarial cases, final-line
  terminator rejection, branded immutable data, no ambient/import access in the
  constrained context, pre-decode byte limiting, and regular-file versus
  symlink/directory/FIFO/archive/malformed/oversized-file cases.
- Both test jobs ran in nonroot containers with no network, a read-only filesystem,
  dropped capabilities, no-new-privileges, bounded CPU/memory/PIDs and tmpfs scratch.
  The containers used `--rm`; hosted post-job cleanup completed. The constrained
  JavaScript context is an access test, not itself an OS security boundary.
  Growth-safe MAX+1 allocation and descriptor metadata checking were source-reviewed;
  a concurrent file-growth race was not runtime-qualified.
- [CodeQL 41355445075](https://github.com/patchwerks/furbomek/actions/runs/41355445075):
  actions, C/C++, JavaScript/TypeScript and Python analyses passed.
- [Broader qualification 41355531848](https://github.com/patchwerks/furbomek/actions/runs/41355531848):
  the accepted advisory workflow completed on the same implementation revision
  under Node 22 and 26. Build, types, offline install and tree checks passed.
  Root inspection of both artifacts found all four new package `.mjs` files with
  **zero errors, warnings and fatal errors**. The whole repository still reports
  36 errors and 23 warnings (candidate lint status remains nonzero); this is not a
  whole-application lint-clean claim. The workflow's historical `fb7` baseline
  is distinct from this PR's accepted `cdd9147` base. Existing application lint
  debt is tracked separately in [PR 40](https://github.com/patchwerks/furbomek/pull/40).

This evidence-only child changes this document and leaves package source, tests,
workflow, root source/configuration and dependencies byte-identical to the tested
implementation revision. Broader qualification is retained for that code revision;
new exact-head extension and CodeQL checks are still required on this document
revision. Candidate-authored checks remain advisory. Independent `pysol-dev`
approval is required before integration; issue 32 remains open for the wider
extension platform and viewer. No merge, deployment or physical qualification is
claimed.

## Changelog

- 2026-11-02: Appended observed hosted test, CodeQL and broader qualification
  evidence after parent review; preserved initial preparation history and limits.
