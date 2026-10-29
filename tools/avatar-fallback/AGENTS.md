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
live broker integration from these fixtures. Do not edit root CI for this slice.
