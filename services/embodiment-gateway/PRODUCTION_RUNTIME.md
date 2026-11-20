---
created: 2026-11-20T12:50:00Z
branch: codex/production-wave-08
author: Codex
status: active
---
# Private production coordinator

`production_runtime.py` owns one serialized controller for the typed owner HTTP
API and opt-in MCP tools. `EdgeSettings.production` defaults to `None` and
`edge-mcp SOCKET` keeps the original seven tools. `edge-mcp SOCKET --production`
adds the production catalog resource and closed status, effect, preset, reaction,
source and bounded movement tools. No model argument selects paths, assets,
shell commands, provider endpoints or physical permissions.

The operator-local `ProductionSettings` selects an existing private media mailbox,
a separate private state directory, actor identity, validated curated packs and
optional HTTP bootstrap secret and reviewed built studio directory. The mailbox and store enforce their exclusive
locks and owner-only modes. There is no default renderer, provider, sound engine
or robot adapter. The coordinator uses the real consumer receipts described in
[the effects contract](../../tools/kinect2/effects/README.md).

Effect apply and revert require observed consumer owner/revision CAS. A submission
without its exact ACK returns HOLD and is never retried. HTTP and MCP use the same
controller epoch/revision fence. Preview and typed save can work while media is
unavailable; dispatch cannot. Saved configuration is stored only at the configured
state root's `owner-preset.json`, and startup reload never dispatches it. HTTP
shutdown precedes scheduler cancellation and release of private resource locks.

Production stage status and bounded movement remain **HOLD**. No operation opens,
rearms, resets or issues a physical production permit. Existing supported-bench
admission stays on the separate local operator socket. Terminal robot STOP reaches
the existing bench adapter before bounded media cleanup.

`ProductionRuntime.observe(Frame, authenticated_sources=...)` is a trusted local
adapter interface, not an HTTP/MCP DTO. Enrollment must bind its sources outside
payloads and use the scheduler's host monotonic clock. The selected Task21 framing
policy is mapped through Task23 into a short-lived renderer ROI/transition, with
an actual consumer ACK. Installing a framing preset alone returns saved
configuration, never an assertion that the program camera moved.

Source deliveries are bound independently to each local/remote authenticated
transport's configured source and scope. Claimed source strings cannot enroll a
provider. `acknowledge` selects `viewer-reaction`; `liquidation` selects the canonical
liquidation pack. Providers cannot supply graphs, priority, commands or permissions.

The fixed `production-projection.json` in the private state directory contains only
at most 64 scheduler resource/status values, a timestamp and 1000ms freshness bound.
It explicitly reports `HOLD_not_enrolled` for the existing activity broker. Task16
must separately enroll that typed projection without forwarding event identities,
raw activity or provider values. Existing Hermes activity publication is unchanged.

## Non-live acceptance

Run the gateway's locked pytest, Ruff and basedpyright checks. The
`test_production_mcp.py`, `test_production_socket.py` and
`test_production_runtime.py` scenarios use actual MCP stdio, private Unix sockets,
loopback HTTP, SQLite and a real Godot consumer with synthetic input. Import the
Godot project assets first in a fresh worktree. These checks do not establish a
live provider session, private installation, captured audio, physical motion or
actual-camera framing qualification; those remain separate Task16 acceptance.
