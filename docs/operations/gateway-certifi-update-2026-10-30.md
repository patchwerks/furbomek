---
timestamp: 2026-10-30
branch: codex/13-update-mcp-sdk
author: Codex security subagent
status: proposed; not deployed
---

# Gateway certifi security maintenance — 2026-10-30

**Observed:** this #13 follow-up to PR #26 changes only the certifi package
record in `services/embodiment-gateway/uv.lock`, from 2026.7.22 to
**2026.10.19**. Incremental certifi base revision:
`575030bb27e882a6af6c1ddd355e3f94ca3ba662`, which already includes MCP 1.30.0.
This follow-up is on PR #26's `codex/13-update-mcp-sdk` branch; the original PR
base is `9347304e866ca90e8eec2d85f3bd3c41002d9a42`. The complete PR changes
both MCP and certifi, as distinguished in the
[MCP maintenance record](gateway-mcp-update-2026-10-30.md).
Within this incremental certifi delta, there are no source, manifest, test,
HTTP transport, or other dependency version changes.
The existing MCP stdio entrypoints and all robot policy boundaries are preserved.

## Advisory and release selection

The [official certifi advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
identifies compromised intermediate keys chaining to emSign ECC Root CA - G3.
Its machine-readable range first fixes 2026.10.18; its prose recommends
2026.10.19 or later because that release restores unaffected emSign roots.
The [PYSEC alias](https://api.osv.dev/v1/vulns/PYSEC-2026-4320) uses 2026.10.19.
[PyPI release metadata](https://pypi.org/pypi/certifi/2026.10.19/json)
confirms the non-yanked universal wheel was published 2026-10-20, requires
Python >=3.7, and has SHA-256
`42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b`.
2026.10.19 is the explicitly recommended fixed release, not a claim of latest:
PyPI also listed 2026.10.23 when checked.

uv 0.11.7 ran `uv lock --upgrade-package certifi==2026.10.19 --no-build`
against the public PyPI index in a clean worker. Parsed comparison confirms
identical top-level lock metadata and package names, with exactly one changed
package object (certifi and its artifacts). HTTPX remains 0.28.1, httpcore 1.0.9,
and MCP 1.30.0. Candidate lock SHA-256:
`0605af975b9c6956e940993a86e86b1b909df419a9d792749167bc2e285a250a`.

## Executed non-live verification

Frozen wheel-only dependencies were installed with `uv sync --frozen
--no-install-project --no-build` in fresh external environments using trusted
Python 3.12.14 on macOS arm64. No project build hook ran. An environment-local
`.pth` entry supplied the gateway source for subprocess/import tests.

The candidate passed all **121 existing pytest tests**, Ruff check, Ruff format
check, basedpyright (zero errors/warnings/notes), and `uv lock --check --offline`.
No test was changed, skipped, or weakened. The suite retains its actual PTY fake
wire and MCP stdio lifecycle coverage. Execution used an empty inherited
environment, denied user-home/real-device access, and denied external networking;
only loopback fixtures and allocated PTYs were permitted. Installation used
public registry access before candidate execution.

An independent offline evidence script parsed certificate DER bytes, rather
than relying on version strings. The old official-wheel bundle contained 121
roots; the candidate contains 120. Exactly one root was removed, with none
added: emSign ECC Root CA - G3, SHA-256
`86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b`.
The fingerprint matches the old published bundle's certificate comment and its
computed DER digest. The candidate bundle byte-matches the
[official tagged source](https://raw.githubusercontent.com/certifi/python-certifi/2026.10.19/certifi/cacert.pem),
SHA-256 `50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`.

Actual SSL context construction loaded the candidate bundle with `CERT_REQUIRED`
and hostname checking enabled. A wrapping spy on the real SSL factory confirmed
HTTPX's unchanged default consumer passes exactly `cafile=certifi.where()`;
its source is byte-identical across environments. No socket or TLS handshake
was attempted.

The trusted Codex interpreter additionally preloads this same root as an
explicit **rejected** certificate (`Rejected Uses: Any Extended Key Usage`).
An initial assertion that it must be absent from `get_ca_certs()` therefore
failed: enumeration includes rejected certificates and is not a trust verdict.
The corrected check accounts for that pre-existing rejection separately and
compares the remaining context certificates with the candidate bundle. No
runtime trust policy, custom CA, or interpreter file was changed. This evidence
establishes bundle removal and unchanged consumer verification settings, not
live TLS acceptance/rejection on another interpreter or deployment host.

Private evidence retains advisory/PyPI metadata, exact parsed lock delta,
restricted-worker profiles, check logs, verification script, and rejection flags.

## Limits, review and rollback

No deployment, provider request, real serial access, robot action, Hermes
configuration, or firmware change occurred. This dependency fix does not qualify
hardware behavior. Independent review and publication remain pending; the wider
security issue stays open. Revert this lock-only change and rebuild a frozen
environment to reproduce the prior state, but that restores the vulnerable
bundle and is not a security remediation.
