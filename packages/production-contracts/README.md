---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-02-task-04
author: patchWERKS / Codex
status: active
---
# Production cue contracts

**Observed:** strict Python DTOs in
[effect_contracts.py](../../services/embodiment-gateway/src/furbomek_gateway/effect_contracts.py)
and [reaction_contracts.py](../../services/embodiment-gateway/src/furbomek_gateway/reaction_contracts.py)
own these generated JSON schemas. This is offline contract validation, not an
installed scheduler, provider connection, actuator grant or rendering proof.

From the repository root:

```sh
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema --check
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema --validate packages/production-contracts/fixtures/liquidation.json
```

Export is deterministic UTF-8 sorted-key JSON with a trailing newline. `--check`
compares exact bytes and exits 1 for missing or changed schemas. `--output` selects
an operator-owned export directory. `--validate` only parses bounded local input;
it reports `dispatch: false`. No command contacts a provider or opens a device.
JSON Schema covers structure; Python additionally enforces graph, identity,
receipt consistency and timing rules. Consumers must use the semantic validator,
not treat schema validation alone as admission.

The synthetic liquidation pack coordinates redacted HUD templates, graphics and
catalog SFX with optional qualified motion. It carries no account data, text
from providers, file paths, executable fields or endpoints. Independent nodes
are parallel; `after` edges require completion. IDs and edges are unique, all
references resolve, cycles fail, at most 16 cues fit a 30-second horizon, and
unordered shared-resource or physical cues fail closed. TTL bounds each cue's
execution after start; the scheduler must additionally enforce event freshness
at admission and dispatch. Cancellation cancels pending cues and stops active
ones. Fault cancels the pack; unavailable cues explicitly skip or cancel it.

The reviewed capability registry supplies resource/physical classifications and
required state. Availability is a contract ceiling, not live health. Media
adapters must still prove readiness; motion remains unavailable until separate
qualified runtime admission. Voice and face remain reserved and unavailable.
The closed RGB/XYZ graphics presets do not imply implemented renderer support.
New effects (including framing or palette extensions) require a reviewed,
versioned adapter and typed DTO update, never execute strings. An applied receipt
binds effective parameters, capability, resource, owner and an increasing revision;
it is not proof of physical motion. Runtime owners must compare it to the actual
request and current ownership before restoring state.

Private events include source, account/stream scope, stable ID, causation, adapter
origin, occurrence/receipt time, freshness cap and replay window. Null, unknown,
future and stale ages fail; dispatch callers must supply trusted current time to
`require_fresh`. Default ephemeral age cap is 10 seconds. Provider envelopes have
no priority field; packs only express curated priority. The future scheduler owns
STOP, owner and Hermes priority through trusted admission paths. `origin: adapter`
is a shape, not authentication: adapters must bind source/scope from authenticated
transport, never from public text. Do not project this envelope to renderers.

`dedupe_key` is `(source, scope, stable_id)` and excludes pack/causation changes.
Task 13 must atomically reserve and persist these keys across restart until at
least `retain_until_ms` (receipt plus replay window). This package provides no
persistence or replay execution. Existing
[extension-preview](../extension-preview/README.md) and
[private character feed](../../services/hermes-activity/CHARACTER.md) remain
separate contracts; neither silently grants these capabilities or accepts packs.
