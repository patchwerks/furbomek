---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-15
author: patchWERKS / Codex
status: active
---
# Private production studio

Task 15 of the approved motion/effects/reactions plan. **Observed:** a standalone
Vue authoring app and explicit synthetic loopback fixture. It does not connect to
Hermes, the legacy proxy, OBS, camera, audio providers or a robot. Task 14/16 owns
live API integration and acceptance. Opening `/` shows live API unavailable;
only `/?mode=fixture` requests `/fixture/` endpoints. Fixture responses must carry
`mode: fixture`, synthetic origin, epoch, owner and applied revision.

From the repository root (Node 22.22.3+ with native TypeScript support, npm, and
the gateway's locked uv environment):

```sh
npm ci --prefix apps/production-studio
npm --prefix apps/production-studio run build
npm --prefix apps/production-studio run qa -- --fixture all
npm --prefix apps/production-studio run fixture
```

The last command prints a random-port `http://127.0.0.1:PORT/?mode=fixture` URL.
It serves the built app, binds only IPv4 loopback, rejects unexpected Host and
cross-origin/non-JSON writes, and has no provider/network/device adapters. It is
an unauthenticated synthetic test surface, **not** an owner-authenticated live
server. Stop with Ctrl-C: its state directory is removed. Never expose or proxy
this fixture publicly. Applied/saved state persists within a fixture state file;
the contract QA restarts against that file to verify stale marking and explicit
reconnect. The ordinary preview command intentionally starts clean each time.

`qa -- --fixture all` starts isolated fixture servers, checks the HTTP contract,
uses the canonical Python reaction validator, writes `.qa/{happy,failure,cleanup}.json`
and stops the servers. Set `STUDIO_EVIDENCE_DIR` to place artifacts in an active
attempt directory. No browser or browser dependency is installed by npm.

For OMO browser QA, set the installed skill path and the URL emitted by `fixture`:

```sh
OMO_BROWSER_SKILL=/path/to/omo/skills/browser \
STUDIO_URL='http://127.0.0.1:PORT/?mode=fixture' \
STUDIO_EVIDENCE_DIR=/private/evidence/task-15 \
bun apps/production-studio/tests/browser.mjs
```

This runner uses installed Google Chrome through OMO's owned pipe engine. It
creates a disposable profile, drives actual controls, captures 390/1440/1920
light/dark top/end views and failure flows, then closes the browser and deletes
the profile. It does not use the owner's Chrome profile. Start a fresh fixture
for reproducible QA; the runner intentionally changes that fixture's state.

## Contract and data ownership

- [Generated production contracts](../../packages/production-contracts/README.md)
  remain authoritative. `npm --prefix apps/production-studio run contracts`
  generates Zod parsers/types from the checked-in schemas; build rejects drift.
  The server calls the canonical Python semantic validator for cue graphs before
  saving or dry-running. Structure alone never grants admission.
- [Kinect inventory](../../tools/kinect2/effects/inventory.json) supplies categorized
  implementation metadata. `implemented` is explicitly different from runtime
  readiness. Inventory selection only inspects metadata; the separate capability
  picker authors the three available synthetic media effects.
- The fixed RGB preview is an explicitly labelled synthetic RGB pattern, never
  optical capture. Other looks validate parameters but show renderer unavailable;
  they are not falsely rendered. Reserved voice/face and motion have no apply or
  preview path. Conditional movement from the liquidation fixture is retained
  read-only and skipped in the dry-run.
- Framing is a **local draft** matching Task 10's candidate renderer fields:
  exact stable `subject_id`, 1–600 ms TTL and unique ordered `subject`, `fixed`,
  `hold` rules. Saving does not submit a renderer envelope or camera command.
  The integration owner must verify the final Task 10 schema before live wiring.
- Saved presets contain exact applied effect, edited reaction, framing draft and
  synthetic event binding. Provider subscriptions are unavailable. Revert and
  restore are explicit, revisioned actions. A network error clears preview and
  disables writes; polling never overwrites a dirty draft. A new epoch invalidates
  pending previews. No credentials, arbitrary paths or code editor exist.

## Limits and rollback

This is fixture-qualified UI, not runtime or physical qualification. The local
fixture does not implement the live scheduler, lease expiry or authenticated
operator session. Those are never inferred from a synthetic receipt. Remove the
app directory or revert its scoped commit to roll back; it changes no installed
service, profile, root dependency lock or hardware. The app bundles the existing
Ioskeley font under its [OFL notice](public/IoskeleyMono-OFL.txt).
