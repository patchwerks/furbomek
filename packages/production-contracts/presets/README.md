---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-09-task-26
author: patchWERKS / Codex
status: candidate
---
# Canonical rehearsal presets

**Observed:** these data-only packs parse through the authoritative
[reaction contracts](../README.md) and produce nondispatch dry-run timelines.
They contain no event, audience text, account identity or runtime authority.
Task 14 owns trusted intent binding; Task 16 owns private Hermes/OBS rehearsal.
Installing these files alone neither subscribes to events nor enables output.

| Preset | Curated intent binding | Parallel cues from 0 ms |
| --- | --- | --- |
| [liquidation](liquidation.json) | `liquidation` → `liquidation` | Generic liquidation HUD, 50% intensity graphics and 30% gain SFX; each ends at 1000 ms |
| [viewer reaction](viewer-reaction.json) | `acknowledge` → `viewer-reaction` | Generic neutral HUD ends at 1000 ms; 25% gain acknowledgment SFX ends at 500 ms |

The viewer preset does not change the camera look. Bind only the authenticated,
moderated adapter's typed intent; never interpolate a viewer name, message,
amount, account, URL or arbitrary command into a cue. These are curated pack IDs,
not provider-selected tools. Synthetic rehearsal events must remain explicitly
labelled by the private rehearsal harness; these packs are not fabricated events.

**Proposed integration:** the liquidation graphics preset uses the
[supported mapping](../../../tools/kinect2/effects/README.md):
`rgb.crimson.v1` and a smooth 1 Hz pulse for one second. This is a labelled
crimson/RGB fallback, not a claim of measured-cloud input. The reaction schema
has no pulse-frequency field; the reviewed media adapter owns that mapping.
The closed SFX presets refer to the existing local catalog. Its original
half-second tones are not a verified siren; requested gain/duration are bounds,
not measured program loudness or proof of playback. Task 16 must check actual
renderer receipts, audio levels, timing and restoration in the encoded program.

**Motion HOLD:** cower/shake and their transitions are not qualified or supported
by this schema. Both canonical packs therefore omit physical cues and explicitly
use a media-only fallback. An `active`, `sleep` or gait action is not a substitute
for cower. There is no fabricated motion cue to make a preview look enabled.
The separate [contract fixture](../fixtures/liquidation.json) exercises optional
`active` motion with `motion_qualified`, `on_unavailable: skip` and the CLI's
`media_only_hold`; it is not the canonical rehearsal preset or motion approval.
A future physical branch needs a reviewed typed action and individual/transition
qualification before addition. Voice and face stay reserved and are omitted.

Each cue has a finite TTL equal to its duration. Unavailable media skips;
faults cancel the pack, and cancellation cancels pending/stops active cues.
Runtime readiness and current owner/revision receipts still gate media execution
and restoration. A dry run predicts timing only; `planned_media` does not mean
the renderer or OBS is connected or applied anything.

From the repository root, using the frozen gateway environment:

```sh
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema --check
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema --validate packages/production-contracts/presets/liquidation.json
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.export_production_schema --validate packages/production-contracts/presets/viewer-reaction.json
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.reaction_replay --fixture packages/production-contracts/presets/liquidation.json --mode dry-run
uv run --frozen --project services/embodiment-gateway python -m furbomek_gateway.reaction_replay --fixture packages/production-contracts/presets/viewer-reaction.json --mode dry-run
```

Both timelines and every row report `dispatch: false`. These checks require no
provider, device, audio output, OBS instance or persistent service.
