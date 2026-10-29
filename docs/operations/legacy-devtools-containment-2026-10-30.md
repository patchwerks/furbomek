---
created: 2026-10-29T17:49:45Z
branch: codex/13-disable-devtools
author: Codex
status: active
---
# Legacy Nuxt DevTools containment

References [issue 13](https://github.com/patchwerks/furbomek/issues/13). The legacy
Nuxt configuration now disables DevTools by default. This is a configuration
containment slice; installed dependency versions and the wider security backlog
are unchanged. It follows the disablement option in the published
[upstream advisory](https://github.com/nuxt/devtools/security/advisories/GHSA-279x-mwfv-vcqv).

## Observed verification

Base: `9347304e866ca90e8eec2d85f3bd3c41002d9a42`. With Node 22.16.0 and the unchanged
lockfile (Nuxt 3.12.4), `npm ci --ignore-scripts --no-audit --no-fund` completed in
an isolated worker. Lifecycle hooks were disabled; the unrelated root hook did
not build or install the separate server package automatically.

The real installed Nuxt loader was called with `{overrides: {dev: true}, ready:
false}`. Before the change its resolved options reported `dev: true`,
`devtools.enabled: true`, and `@nuxt/devtools` in `_modules`. After the change they
reported `dev: true`, `devtools.enabled: false`, and no DevTools registration.
This exercises Nuxt's actual configuration resolution and module-registration
choice without initializing a development server or RPC listener.

`npm run build` passed both before and after the change, including the configured
type checking and client/Nitro production output. Existing Browserslist and
compatibility-date notices remain; no dependencies were refreshed to hide them.
Both resolution and builds ran with an empty environment, telemetry disabled,
TCP/IP denied, user-home/device reads denied and writes confined to temporary
files and generated build/dependency directories. No provider calls, credentials,
live servers or hardware were used. Whitespace checks passed.

## Limits and rollback

No live development RPC probe or production deployment was performed. The
package remains installed transitively; this change neither upgrades it nor
claims all associated alerts are cleared. Explicit future configuration overrides
must preserve this default until a separately reviewed toolchain update is
qualified. Reverting the one-line setting would restore the old enabled default
and must not be treated as a routine deployment step. Independent review and
final-head checks remain required; issue 13 stays open.
