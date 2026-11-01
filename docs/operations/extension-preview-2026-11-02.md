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
