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

## Private owner HTTP seam (Task 24)

`?mode=live` selects an independent authenticated client. The default unavailable
screen and `?mode=fixture` remain separate. Live mode never imports synthetic
applied state. It displays controller origin, epoch, revision, health and receipts;
lost connectivity marks the last response historical and disables mutation.

The transport is `furbomek_gateway.production_http.OwnerHttpServer`, constructed
with an explicit `ProductionController` and a serve-time `SecretStr` bootstrap
credential (32–128 random URL-safe characters). There is no default controller,
launcher, persistent process or deployed endpoint. Task 14 must supply the real
orchestrator. An optional owner-configured `studio_directory: Path` loads the
built studio into an immutable exact-path map at construction; default API-only
behavior is unchanged. Only index HTML and approved assets are served, with
self-only scripts/styles/connect, frame denial, no arbitrary file paths, and
no symlink traversal. Limits are 64 entries, 4 MiB per asset and 16 MiB total.
Do not expose this listener through a
public proxy. It binds only `127.0.0.1`; Host is its exact IP and port.

- `POST /api/production/session`: exact Origin, `Authorization: Bearer …`, JSON
  `{}`. The response sets an HttpOnly, SameSite=Strict cookie scoped to
  `/api/production/` and returns an in-memory CSRF token. The browser clears the
  bootstrap input immediately. No URL or browser-storage credential is used.
- `GET /api/production/status`: cookie and exact Origin or the same-origin custom
  `X-Owner-Request: 1` header. Navigation and cross-site fetches are refused.
- `POST /api/production/action`: cookie, exact Origin, CSRF header and the closed
  discriminated `OwnerAction` DTO. Every action carries epoch/revision. No raw
  endpoints, paths, renderer mailbox authority, role elevation or physical actions.

Sessions and CSRF expire together after 900 seconds (configured maximum 3600);
8 sessions and 8 HTTP workers are the defaults, request bodies are at most 32768
bytes, and socket reads time out after 3 seconds. The cookie intentionally lacks
`Secure` on this HTTP-only loopback transport; this is not a public TLS service.
HTTP requests fail busy instead of queuing mutations. Authenticated typed
preview and private preset save remain usable under HOLD; apply, revert and
manual dispatch require fresh available controller authority. Cancel is limited
to work owned by this controller. The controller must bound
its calls, atomically fence revisions across **all** writers including MCP,
recheck real readiness, and return actual observed receipts. Transport locking
alone cannot fence other writers. A candidate renderer's unsupported field must
produce a held/rejected receipt, never silent truncation or simulated success.

Canonical DTOs are in `production_http_models.py`, with Task 21 `FramingPreset`
and Task 23 `VisualSettings` imported directly. Regenerate/check the export from
the gateway environment, then regenerate the TypeScript parsers:

```sh
uv run --frozen --project services/embodiment-gateway python -m \
  furbomek_gateway.export_owner_http_schema \
  apps/production-studio/live-contracts.schema.json
node apps/production-studio/scripts/generate-live-contracts.mjs
```

`--check` on each command verifies exact source parity. JSON Schema handles
boundary structure/ranges; the Python canonical model additionally validates
framing references and ROI containment. The controller owns semantic readiness.
Live safe effects exclude physical and reserved capabilities; fixture cue editing
and compact framing drafts retain their existing independent behavior.

`tests/live-browser.mjs` owns an ephemeral Python HTTP fixture server and Chrome
profile, authenticates through the real HTTP seam and checks receipts/refusals.
Its controller is explicitly labelled `injected-test-fixture`, exists only under
gateway tests, and connects to no device/runtime. Run from the repository root
with `OMO_BROWSER_SKILL` and `STUDIO_EVIDENCE_DIR` set. The script closes server,
browser and temporary profile. This proves the API/UI seam, not deployment or
live renderer, OBS, camera, Hermes or robot acceptance.

## Changelog

- 2026-11-20: Added the explicit private owner HTTP/live-client seam and its
  scoped fixture verification. Actual runtime integration remains Task 14.
