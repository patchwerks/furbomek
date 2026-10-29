---
created: 2026-10-29T17:25:39Z
branch: codex/13-express-parser-fix
author: Codex
status: active
---
# Offline proxy verification

References [issue 13](https://github.com/patchwerks/furbomek/issues/13). This covers bounded Express 4 request-parser and proxy-address dependency maintenance; it does not complete the broader dependency-security backlog.

## Run

Use Node.js 22 or later on a Unix host. Run in an isolated, credential-free checkout without production network/device access. Installation and execution are separate steps:

```sh
npm ci --prefix server --ignore-scripts --no-audit --no-fund
npm test --prefix server
node --check server/tts-proxy.js
```

The root package's installation hook builds Nuxt and installs server dependencies. These server-only checks intentionally avoid that unrelated hook; the root package and lockfile are unchanged.

The test fixture runs the actual unmodified `tts-proxy.js`. It replaces only its listener destination with a private temporary Unix socket and supplies synthetic fetch responses. The streamed response uses a real WHATWG `Response` body, matching Node fetch's stream interface. No provider key, production endpoint, TCP listener, OBS, Hermes or robot access is needed. Fixture values named as credentials are inert test strings. The fixture is under `test/fixtures` and is never selected by the normal server entrypoint.

## Behavioral coverage

Six tests cover ordinary JSON and streamed provider bytes, valid compressed JSON, malformed JSON rejection, body-size limits, completed compressed frames followed by trailing bytes, and all four metadata routes. Rejection cases assert that no provider call occurred and that the same child remains responsive. The trailing-data regression expects successful parsing of the completed frame followed by continued process health; it does not claim those trailing bytes produce an HTTP rejection.

Each test owns its child process/socket and removes both during teardown. Tests have bounded startup/request/test timeouts. They do not start `npm run start`, change the normal port/bind policy or invoke real provider APIs.

## Dependency scope and observed evidence

The direct server requirement moves from Express `^4.19.2` to `^4.22.3`; the lock resolves Express 4.22.3 and body-parser 1.20.9 through Express's compatible `~1.20.5` range. Related lock changes are within the Express dependency closure. CORS remains at its existing version, and no dependency overrides or direct parser dependency are introduced. This is not a blanket claim that all server or repository alerts are resolved.

The parser update addresses the published [body-parser compressed-body advisory](https://github.com/expressjs/body-parser/security/advisories/GHSA-27r3-jxmh-p828). Its regression shape is informed by the [upstream JSON parser tests](https://github.com/expressjs/body-parser/blob/1.20.9/test/json.js); no external reproducer is executed.

On both Node.js 22.16.0 and 26.7.0, the identical trailing-frame test against the original lockfile reproduced an unhandled Gunzip error and child exit 1. With this lockfile, all six tests passed and the child served a subsequent request. Validation used an empty environment and a worker denying user-home/device reads, source writes and TCP/IP networking, with only temporary-directory writes and Unix sockets permitted. Dependencies were installed separately with lifecycle scripts disabled.

CodeQL/hosted checks must be inspected at the final PR head before acceptance. No merge, deployment, real provider test or installed-service qualification is implied. Rollback restores the preceding server manifest/lock; the proxy runtime source has not changed.

## Proxy-address follow-up (2026-10-30)

**Observed:** Only the `proxy-addr` lock entry changes from 2.0.7 to 2.0.8,
within Express's existing `~2.0.7` requirement. All other package entries,
both manifests and the independent root lock remain unchanged; no override is
needed. The [advisory](https://github.com/advisories/GHSA-jqcg-44mw-7w3h)
affects `>=1.1.0, <2.0.8`; see the [2.0.8 release](https://github.com/jshttp/proxy-addr/releases/tag/v2.0.8)
and [upstream fix](https://github.com/jshttp/proxy-addr/commit/780911d).

Seven additional offline tests use the installed dependency and Express request
getters on synthetic requests. Short mapped IPv6 `/8` and zero-leading `::/1`
trust subnets must not trust arbitrary IPv4 peers, including mapped client forms;
both single and multiple-subnet paths are covered. Plain IPv4 `/8` and correctly
mapped `/104` controls retain allowed/rejected peers. The default Express policy
ignores forwarded address claims. On Node.js 22.16.0, the prior 2.0.7 dependency
fails all four problematic-subnet cases while the three controls pass; 2.0.8
passes all 13 tests, including the six unchanged actual-proxy tests above.

Preparation used a registry tarball checked against its SHA-512 integrity and a
locked offline install with hooks disabled. Tests used an empty environment in a
worker denying user-home/device reads and TCP, permitting temporary writes and
private Unix sockets. The runtime proxy does not configure `trust proxy` or use
`req.ip` for authorization: these fixtures demonstrate the dependency defect,
not exploitation of the deployed service. No runtime policy, live provider,
listener configuration or deployment changes are included. Other dependency
findings remain outside this slice; rollback restores the preceding server lock.

## Changelog

- 2026-10-30: Confirmed six passing tests and the original-lockfile failure on checksum-verified official Node.js 22.16.0; corrected creation timestamp to the file creation record.
