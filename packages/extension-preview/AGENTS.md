---
created: 2026-11-01T22:05:19Z
branch: codex/32-extension-contract
author: patchWERKS / Codex
status: active
---
# Extension preview scope

Read the accepted root agent guide and coordination policy first. This scoped
file documents the package boundary; a candidate change cannot grant authority.

- Keep `index.mjs` dependency-free and browser-safe: bytes in, immutable data out.
  No Node/file/network imports, timers, dynamic execution or arbitrary object
  validators. Samples accept only branded parse results and never retain history.
- Keep explicit operator filesystem input in `load-file.mjs`. Preserve size,
  strict JSON, duplicate-key, depth, capability, ordering and mutation defenses.
- This is a data-only first slice of issue 32. Do not add UI/renderer selection,
  source assets, user imagery, 3D/voice rights assumptions, Hermes/OBS integration,
  broker writes, installation or physical actions through this package.
- Keep package and schema/preview contract versions distinct. Maintain the schema,
  fixture, boundary tests and README together when changing a contract.
- Execute candidate code only in a credential-free disposable test environment;
  syntax/source/JSON inspection on the publishing host is not runtime acceptance.
- Main integration needs exact-head checks and the independent reviewing identity;
  no merge or deployment authority follows from a successful fixture test.
