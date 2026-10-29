---
timestamp: 2026-10-29T18:28:12Z
branch: codex/13-update-mcp-sdk
author: Codex security subagent
status: proposed; not deployed
---

# Gateway MCP SDK maintenance evidence — 2026-10-30

This bounded #13 slice updates the embodiment gateway's exact MCP SDK pin from
1.27.1 to **1.30.0**, based on published main
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. No gateway behavior or test changes
were needed. A stale version in the registration module's docstring is removed.

## Version selection and scope

The [official 1.30.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)
is the newest 1.x maintenance release verified on 2026-10-30. The upstream
[security policy](https://github.com/modelcontextprotocol/python-sdk/blob/main/SECURITY.md)
supports the newest maintenance release for applications remaining on 1.x.
Official advisory patched ranges were reviewed before choosing the pin; this
is not a 2.x migration or an assertion that every advisory affects this gateway.

Both CLI entrypoints retain explicit `transport="stdio"`. No HTTP, WebSocket,
experimental task handler, new tool, authorization bypass, or device enrollment
is added. Existing STOP/cancellation, action allowlist, mutation non-retry,
normal DISARM, and operator-local settings boundaries remain unchanged.

The lock was regenerated with **uv 0.11.7**, matching the established project
validation tooling, using `uv lock --upgrade-package mcp`. Lock revision 3 is
preserved. The resolver adds four Python-version/platform resolution markers.
Only the MCP package changes version/artifacts; **zero other package objects
change**, zero packages are added/removed, and project metadata changes only
the exact MCP requirement. Pytest remains **9.1.1**. No bulk refresh or constraint
relaxation was used.

## Executed offline compatibility checks

Separate baseline and candidate environments used **Python 3.12.14**, macOS
arm64, and locked wheel-only dependency installations. Project build hooks
were not executed: `uv sync --frozen --no-install-project --no-build` installed
the dependencies, and a disposable environment-local `.pth` file pointed to
the corresponding unchanged source tree. This tests imports/subprocess behavior;
it does not qualify package-wheel building or deployment.

Tests ran with an empty inherited environment except explicit tool paths and
temporary-directory settings, user-home reads denied, real device paths denied,
and external network denied. Only loopback test fixtures and allocated macOS
PTY pseudo-devices were available. Directory lookup under `/dev` was allowed
for `ttyname`; real serial device files were not allowed. No hardware, production
service, Hermes enrollment, provider call, or OBS session was accessed.

| Check | Baseline 1.27.1 | Candidate 1.30.0 |
| --- | --- | --- |
| `python -m pytest -q` | 121 passed | 121 passed |
| `ruff check .` | passed | passed |
| `ruff format --check .` | passed | passed |
| `basedpyright` | 0 errors/warnings/notes | 0 errors/warnings/notes |
| Actual registered tool catalogs and schemas | baseline | identical |

The existing suite exercises real MCP stdio subprocess initialization/calls,
stock motion rejection before socket access, actual simulated PTY wire traffic,
shielded cancellation/STOP delivery, partial replies, timeout/retry boundaries,
and normal DISARM after bounded actions. No existing test was skipped or weakened.

A separate constructor-only check collected each actual `list_tools()` result
without entering a server lifespan or opening a device. All fields (including
input/output schemas and annotations) match across the stock **4-tool**,
motor-off **6-tool**, and supervised **5-tool** catalogs. Canonical JSON SHA-256:
`be513d5ce1a80ecc1c83bb9d47ad626abd4ae4828ea88804a9df928916154cc6`.
The standalone baseline snapshot emitted a Pydantic settings forward-reference
warning; the candidate did not. Snapshot warnings were retained separately from
JSON, not suppressed or mistaken for a schema difference.

The final lock also passed `uv lock --check --offline` using uv 0.11.7. Worker
profiles, exact lock comparison, test logs, and tool snapshots are retained in
the private review evidence. Hosted CodeQL status is reported on the PR, separately
from these local tests.

## Limits and rollback

No deployment, physical robot action, real serial endpoint, remote MCP host,
HTTP/authentication service, or operating-system matrix was tested. Simulated
success does not establish physical safety or authorization to operate hardware.
The wider security issue remains open. Revert the manifest and lockfile together
and recreate the environment from the prior frozen lock to roll back this slice.
