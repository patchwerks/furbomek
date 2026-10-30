---
created: 2026-10-29T16:57:52Z
branch: codex/5-avatar-fallback
author: Codex
status: active
---
# Static fallback

This directory owns the offline static renderer preparation for Furbomek #5.
Preserve the read-only PLAN §6.5 surface, bundled assets and explicit fixture entrypoint.
No transport, credentials, OBS controls, speech runtime or robot capability belongs here.
The ordinary index must remain offline by default. Never load fixture.js from index.html.
Run `node --test tools/avatar-fallback/tests/*.test.mjs` from the repository root.
Browser/OBS acceptance is separate from unit tests; do not claim private recording or
live broker integration from these fixtures. The reviewed
[avatar fixture workflow](../../.github/workflows/avatar-fallback.yml) is the only
repository CI surface in this slice; changes remain limited to offline avatar
fixture validation and require independent review. Other repository CI is outside
this scope. Preserve credential-free, disposable test execution and all network,
private-home and device restrictions.

The private ten-minute OBS/CEF test must wait for access to Brodex from Xeno and
an exclusive designated-operator window. Offline tests do not satisfy that gate.

## Changelog — 2026-10-30

Replaced the obsolete blanket root-CI prohibition with the narrow reviewed avatar
fixture workflow scope and recorded the pending Brodex access gate. No runtime or
workflow behavior changes accompany this documentation correction.
