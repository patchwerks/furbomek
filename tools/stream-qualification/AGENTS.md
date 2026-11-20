---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-10-task-27
author: patchWERKS / Codex
status: active
---
# Offline gate ownership

Keep this directory dependency-free under standard Python 3.11+. Its fixture
matrix is an admission-policy replay, not the gateway or hardware simulator.
The strict parser owns untrusted input. No receipt, supplied PASS field, digest,
clock window or synthetic fixture may authorize release or live I/O.

`approved-live` must refuse before reading its manifest until a separately
reviewed installed trust/instrumentation integration exists. `release-check`
may diagnose only an explicitly supplied bounded local JSON file; it must not
resolve payload paths, load devices/providers or execute commands.

Run the CLI and `python3 -m unittest discover -s tools/stream-qualification/tests
-v` from the repository root, plus the repository's Ruff checks. Preserve source
and input digests and distinguish actual arithmetic/CLI evidence from unmeasured
broadcast, stage, stop, battery and 24-hour behavior.
