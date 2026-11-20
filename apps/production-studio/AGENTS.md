---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-15
author: patchWERKS / Codex
status: active
---
# Production studio

Read the root and pinned coordination instructions. This standalone Vue app owns
private owner authoring only; it must not import legacy provider code or the
presentation pack viewer. Exact npm pins and the app lock are authoritative here.

- Default route is unavailable. Explicit `mode=live` uses the authenticated
  owner HTTP seam with a caller-injected controller; deployment is separate.
  Explicit fixture mode uses only `/fixture/` and validates synthetic provenance.
- Never turn implementation inventory metadata into runtime readiness. No raw
  control, endpoint/path, calibration, admission or rearm UI.
- Generate `src/generated.ts` from canonical Task 4 schemas, never edit it. Keep
  graph semantic validation in the Python owner; do not clone its admission rules.
- Framing drafts do not dispatch. Live framing imports Task 21's
  canonical versioned schema; compact fixture framing remains fixture-only.
- Preserve exact revision/epoch comparisons, dirty drafts across polling and
  reconnect, explicit revert/restore, invalidated previews and bounded requests.
- `fixture/` is an isolated test server, never an authenticated live deployment.
  Bind loopback, check origin/host, clean state files and close listeners after QA.
- Build and real browser evidence are required for changes. Follow DESIGN.md,
  capture light/dark phone/desktop states, and keep screenshots out of commits.

## Changelog

- 2026-11-20: Explicit live owner mode and canonical HTTP DTO generation; no
  default controller or deployment.
