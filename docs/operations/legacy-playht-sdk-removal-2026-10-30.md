---
timestamp: 2026-10-29T18:10:22Z
branch: codex/13-remove-unused-playht-sdk
author: Codex security subagent
status: independently source-reviewed; draft proposal; not deployed
---

# Legacy PlayHT SDK removal evidence — 2026-10-30

This is one bounded dependency-reduction slice of #13, based on published main
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. It removes the unused root npm
`playht` dependency. The local PlayHT voice integration is preserved.

## Source and dependency review

- `app.vue` imports `PlayHtTTS` from `~/src/tts/playht` and retains its provider
  selection. `src/tts/playht.ts` uses browser fetch through the existing proxy;
  it does not import the npm SDK. Its imports are local TypeScript types.
- Tracked source/config review found no static import, dynamic import, require,
  or indirect loader for the npm `playht` package. The browser's explicit
  dynamic SDK import is for `@deepgram/sdk`.
- Only the root dependency declaration and its now-unused lockfile entries
  change: 28 package entries removed, zero added, and zero retained package
  entry changes. No retained dependency version changes. The root lock metadata
  removes the same direct dependency.
- Application source, settings/provider selection, proxy source, server lockfile,
  framework versions, and workflows are unchanged.

## Executed local validation

Node **22.16.0** on macOS arm64; installation hooks disabled, empty credentials
environment, filesystem access restricted, and **all network denied** during
builds. No development server, provider calls, audio devices, or live services
were used.

1. Installed the original lockfile with `npm ci --offline --ignore-scripts
   --no-audit --no-fund`: 971 packages.
2. Built the original application in production mode with Nuxt's actual loader,
   type preparation, and build APIs. An observer Vite plugin collected the
   module IDs in emitted chunks without modifying code or bundles.
3. Removed only the direct manifest dependency; regenerated the lock with
   `npm install --package-lock-only --offline --ignore-scripts --no-audit
   --no-fund`. Compared every retained lockfile package object against base.
4. Reinstalled the revised lock with the same offline `npm ci` command:
   943 packages. Confirmed `node_modules/playht` is absent.
5. Repeated the production build with the same observer: **passed**, including
   the configured type checking and Nitro server build. Both builds emitted the
   identical set of **159 module IDs**, including `src/tts/playht.ts`; neither
   included the npm SDK. Normalized graph SHA-256:
   `791fc76f0e94d5457f271ba04abc3f660a91f84828980de9b176b77f439ab541`.
6. All **six emitted client JavaScript assets** had identical paths and SHA-256
   hashes before and after. The complete output tree was not byte-identical:
   generated build metadata and the server runtime differed across runs.
7. `git diff --check` passed. Existing Browserslist and Nuxt compatibility-date
   notices appeared on both builds.

The build observer used the installed `nuxt/dist/index.mjs` exports `loadNuxt`
and `build`, plus `writeTypes` from `@nuxt/kit/dist/index.mjs`, in this order:
`loadNuxt({ready:false, overrides:{dev:false}})`, register `vite:extendConfig`,
`nuxt.ready()`, `writeTypes(nuxt)`, `build(nuxt)`, then `nuxt.close()`. Its
`generateBundle` hook reads each chunk's `modules` keys into a sorted set and
normalizes the checkout prefix to `<root>`. `NODE_ENV=production` and
`NUXT_TELEMETRY_DISABLED=1` were set for both runs. Evidence logs and graph/hash
inventories are retained locally with the review record.

## Limits and rollback

These checks establish that the removed SDK does not contribute to the current
production bundle and that the existing integration still compiles unchanged.
They do not validate PlayHT's current remote API, live speech/audio behavior,
or the broader security issue. Revert the manifest and lockfile together and
reinstall the lockfile to restore the removed dependency. This slice does not
change the separate DevTools containment or Express parser proposals.
