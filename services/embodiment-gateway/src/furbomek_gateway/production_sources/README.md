---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-12
author: Codex production_source_adapters
status: active
---
# Private production source ingress

**Observed, non-live:** source normalization, authenticated local delivery,
provider session state machines and a local CLI are implemented. Synthetic
provider-spec fixtures exercise the complete collector → signed delivery →
strict `PrivateEvent` route. No real OAuth token, account, provider connection,
chat send, signing transaction, trade, deployment or actuator was used.
Concrete TLS WebSocket and Twitch HTTPS transports are implemented and verified
against owned loopback TLS servers. Live enrollment remains **held** pending
explicit authorization and private host acceptance; no backend starts implicitly.

## Callable boundary

- `TwitchAdapter(TwitchPolicy, key).receive(raw, now_ms) -> SourceResult`
- `HyperliquidAdapter(HyperliquidPolicy, key).receive(raw, now_ms)
  -> tuple[SourceResult, ...]`
- `TwitchSession(adapter, transport, signer).poll(clock)` receives welcome,
  creates the typed chat-read subscription through the enrolled transport,
  follows an origin-checked reconnect and preserves adapter state. A reported
  `ConnectionError` clears subscription enrollment, so the next welcome
  resubscribes without clearing dedupe. The transport retains the old socket
  until replacement welcome, applies keepalive deadlines, cancels bounded reads,
  and raises on disconnect. These behaviors have loopback coverage; actual provider
  acceptance remains held.
- `HyperliquidSession(adapter, transport, signer).start()` subscribes only to
  `userEvents` and `userNonFundingLedgerUpdates` for the configured account;
  `.poll(clock)` handles a bounded ledger batch. Reuse the adapter across socket
  replacement, call `start()` again, and continue treating snapshots as inert.

`provider_socket.ProviderSocket(source).opened()` opens only the fixed provider
WSS endpoint with certificate/hostname checks, no proxy or redirects, 64 KiB
frames, four queued frames, 5-second handshake, 10-second receive and 1-second
close bounds. `TwitchSocket(socket, TwitchApi(explicit_credentials))` supplies
the Twitch session interface. `TwitchApi` uses fixed validation/subscription HTTPS
URLs, bounded identity-encoded bodies, no redirects, no ambient credentials and
no retries; successful token validation is cached until expiration or one hour.
The explicit credentials bind both the reader and broadcaster. A custom TLS CA
context is supported but cannot disable certificate/hostname checks. Callers own
the socket context and must use the source enabled gate before opening it.

Session `clock` is a trusted host millisecond callable, evaluated after the blocking
receive finishes; fixture tests use a fixed callable. Never supply provider time
as this clock.

The supplied transport must expose its actual TLS-verified peer, not a value
read from provider JSON. Twitch must return an independently validated OAuth
reader ID and `user:read:chat` scope. The collector rejects the wrong peer,
reader or missing read scope before reading or subscribing. Subscription creation
is EventSub management, not a chat send. No OAuth acquisition or live subscription
creation is performed by the fixture probe.

Operator configuration defaults `enabled` to false. Supply explicit broadcaster,
reader/subscription identity or Hyperliquid account, an opaque persistent `scope`,
and source/user caps with a measured-load evidence reference before enrollment.
The fixture caps reference `synthetic-fixture-only`; they are not production load
qualification. Stop/recreate the collector to change policy or clear revocation.

Each collector uses its own private random key of at least 32 bytes. `CollectorSigner`
and `Authenticator` bind schema version, adapter ID, session ID, receipt timestamp
and the exact payload via HMAC-SHA256. This is **local collector authentication**,
not a claimed Twitch or Hyperliquid signature. Keys and policies must stay outside
Git in owner-only files. Never expose the signer through public/model ingress.
`Delivery.signing_bytes()` specifies the canonical encoding for another process.
Unsigned, changed, wrong-source, wrong-session and delayed deliveries fail closed.
The host clock is trusted; receipt delay is capped at 1 second and provider age
at the configured maximum (at most 10 seconds). Duplicate JSON fields are denied.

## Output and authority

`SourceReceipt` contains only a strict version-one `PrivateEvent`, a closed intent
(`acknowledge`, `rgb`, `xyz`, `liquidation`) and fixed preview text. Twitch accepts
only exact `!ack`, `!rgb`, `!xyz` messages after channel, shared-chat origin,
subscription and local moderation checks. Every other string is denied; there
is no prompt interpretation. Operator-maintained blocked user/message IDs are
typed filters, not a claim of synchronous Twitch AutoMod integration.

`SourceDisposition` contains only an observed/denied status and closed reason.
Raw chat, display names, account addresses, positions, amounts and provider
connection URLs are absent from results. `PrivateEvent` is private; renderers
receive the fixed preview, never the entire envelope. Neither output grants a
tool, motor, wallet, OBS or publication capability.

Persist `event.dedupe_key` atomically in Task 13 before any dispatch. Source IDs
are `twitch.eventsub.v1` and `hyperliquid.ledger.v1`; the operator scope must remain
stable across transport/process changes. Stable IDs digest the Twitch chat message
ID or lowercase Hyperliquid ledger hash, excluding transport delivery/session
IDs and timestamps. The process-local gate caps source/user rates over 60 seconds
and retains seen identities for 60 seconds. It is not durable dispatch storage.
Fresh snapshot ledger identities are tombstoned without emitting reactions.
On process restart the downstream durable store remains responsible for consumed
receipts; do not bypass it or substitute the collector's in-memory cache.

## Provider provenance and limits

**Reference/inferred**, accessed 2026-11-20; documentation only, no provider SDK
or third-party implementation copied:

- [Twitch chat reference](https://dev.twitch.tv/docs/eventsub/reference/chat#channel-chat-message)
  specifies version-one `channel.chat.message`, broadcaster/reader conditions,
  `user:read:chat` and the chat event/message fields.
- [Twitch WebSocket lifecycle](https://dev.twitch.tv/docs/eventsub/handling-websocket-events/)
  specifies welcome/reconnect/revocation and user-token subscriptions. WebSocket
  metadata has no webhook-signature equivalent; TLS/OAuth enrollment plus local
  collector authentication is therefore explicit. The documented reconnect
  retains subscriptions; a lost connection requires resubscription.
- [Hyperliquid subscriptions](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions)
  specifies the user stream, snapshot marker and non-funding ledger updates.
  Immediate `WsLiquidation` has `lid` and `liquidated_user`, but no occurrence
  timestamp. It remains observation-only. A ledger liquidation supplies `time`,
  `hash` and the account-bound typed delta; this independently verified event
  authorizes only a curated request. The ledger does not expose `lid`, so no
  one-to-one correlation is claimed or fabricated. The provider prose describes
  initial `isSnapshot: true`, then `false`; the published ledger wrapper definition
  is incomplete. Until scoped evidence resolves omission semantics, a missing
  marker fails closed rather than being treated as a live event.

Fixtures under `tests/fixtures/production_sources/` are synthetic, built from
these documented fields. `SANITIZED_ACCOUNT` and `SANITIZED_HASH` are materialized
only by the test helper into conspicuously repeated synthetic values. They are
not captured user records. Unknown provider fields are discarded by provider
projection models; project delivery/receipt/config contracts forbid extra fields.
Unrelated ledger deltas are denied without interrupting valid entries in a batch.

The lock pins `websockets==15.0.1` (BSD-3-Clause) and makes the existing
`httpx==0.28.1` (BSD-3-Clause) a direct dependency. No upstream code was copied.
[WebSocket sync client](https://github.com/python-websockets/websockets/blob/15.0.1/docs/reference/sync/client.rst),
[HTTPX environment isolation](https://github.com/encode/httpx/blob/0.28.1/docs/environment_variables.md),
[Twitch token validation](https://dev.twitch.tv/docs/authentication/validate-tokens/)
and [EventSub management](https://dev.twitch.tv/docs/eventsub/manage-subscriptions/)
were reviewed as primary references. Transport tests generate ephemeral test
certificates and redirect only the fixed provider hostnames to owned loopback
sockets; they never resolve or contact those provider hosts.

## Local verification

From `services/embodiment-gateway`:

```sh
uv run --frozen pytest -q tests/test_production_sources.py -k 'twitch or liquidation or reconnect'
uv run --frozen pytest -q tests/test_production_source*.py
uv run --frozen python -m furbomek_gateway.production_sources twitch \
  --policy-file /private/path/policy.json --delivery-file /private/path/delivery.json \
  --key-file /private/path/key.bin --now-ms 1795132800100
```

The CLI reads only local files, prints redacted results and exits 2 on denial.
An observed snapshot exits 0 with no receipt. It never dispatches reactions.
The caller supplies trusted time explicitly for deterministic fixture replay;
a live runner must use its trusted host clock. No hardware or provider traffic
is part of these tests.
