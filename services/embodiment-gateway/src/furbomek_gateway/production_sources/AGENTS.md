---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-12
author: Codex production_source_adapters
status: active
---
# Private source ingress

Read the paired README for provider provenance, callable routes and live gates.
This package owns authenticated source normalization and read-only subscriptions.
It cannot dispatch reactions or expose robot, OBS, shell, wallet or chat-send tools.

Keep the strict project envelope separate from provider projection models. Check
TLS/OAuth enrollment independently of event JSON. Provider reconnect IDs cannot
replace durable event identities. Snapshot or untimed events never emit reactions.
Task 13 owns atomic durable dedupe and dispatch; in-memory counters are not proof
of exactly-once output. Never log raw source data or credential values in evidence.

Verification uses the frozen gateway environment, focused production-source tests,
Ruff/format and basedpyright. Transport tests use ephemeral certificates and owned
loopback servers only. Real provider enrollment requires existing explicit
authorization; no tests may read user credentials or contact real accounts.
