---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-13
author: Codex
status: active
---
# Private reaction sequencing

**Implemented, non-live:** `reaction_scheduler`, `reaction_store`, and
`reaction_replay` consume the existing Task 4 contracts. There is no hardware,
renderer, provider or Hermes backend in this change. Physical effects always
produce `media_only_hold`, including an adapter that claims availability.
A future integration must separately qualify and review physical admission.

Use `ReactionStore(path)` as a context manager with a dedicated owner-only
0700 directory outside any Git checkout. The database is 0600, refuses symlinks
and public permissions, and uses full-sync SQLite transactions. A nonblocking
file lock permits one scheduler owner. Keep this context open for the runtime;
close it on shutdown to release ownership. Durable event identity is
`(source, scope, stable_id)`, independent of the selected pack. Call
`store.prune(epoch_ms)` to remove only terminal events strictly after their
source freshness/reconnect retention deadline. Identity and step journals are
private; do not expose `store.steps()` to observers.

Construct `ReactionScheduler(store, adapter, HostClock())`. Construction consumes
interrupted graphs; it never resumes movement or retries an uncertain step.
`submit(event, pack)` fixes priority to curated public presets.
`submit_trusted(event, pack, Priority.ADMITTED)` is for an authenticated local
operator or Hermes admission; `Priority.OWNER` is the local owner override.
Neither method authenticates callers: the integrating private boundary must
supply verified `PrivateEvent` identities and restrict the trusted method.
No provider field can select priority. Both return a private event ID or `None`
for a duplicate/disabled admission; freshness errors raise before insertion.

Call `tick()` from one host loop and feed actual renderer receipts to
`acknowledge(AppliedAck)`. It returns false for unknown, duplicate, stale,
cancelled, mismatched or overwritten receipts. Dependencies wait for acknowledged
completion and bounded duration; conflicts wait only within the cue TTL and
original event freshness. Higher priority cancels the conflicting graph.
`cancel(event_id, reason)` consumes the graph and conditionally releases outputs.
`stop()` immediately invokes the adapter's unconditional stop, latches admission
off and consumes all graphs; it has no priority queue or automatic rearm.
`projection()` returns immutable resource/status/hold-only records, never provider
IDs or arbitrary cancellation text. No observer control method is installed.

The required `ReactionAdapter` protocol is in
[src/furbomek_gateway/reaction_types.py](src/furbomek_gateway/reaction_types.py).
Dispatch must CAS the actual property revision, apply once per unique owner token,
and report an actual applied receipt. Manual changes must increment revision and
revoke ownership even if the value is unchanged. Release must atomically compare
owner and revision, restore only the previous value (without reviving its owner),
or use neutral for an unacknowledged application. Recovery retries only conditional
media reconciliation and idempotent STOP, never dispatch. Adapter operations must
be bounded, raise `AdapterFaultError(resource)` for known dispatch failures, and
enforce their own output TTL; this scheduler is not a robot
watchdog or proof of physical actuation. Exceptions leave the reservation consumed.

Offline CLI from repository root:

```sh
uv run --frozen --project services/embodiment-gateway python -m \
  furbomek_gateway.reaction_replay \
  --fixture packages/production-contracts/fixtures/liquidation.json --mode dry-run
```

This compiles a deterministic predicted timeline without constructing a scheduler,
opening a state database or creating an output adapter. Each row and the entire
result say `dispatch: false`; `planned_media` is a prediction, not an applied ACK.
The motion row says `media_only_hold`. Other modes are rejected.

Verification uses the two focused `test_reaction_scheduler.py` and
`test_reaction_store.py` modules with real SQLite and a test-only CAS renderer and
virtual clock. It does not qualify actual renderer wiring, live connectivity,
robot movement, hardware STOP delivery or power-loss filesystem durability.
