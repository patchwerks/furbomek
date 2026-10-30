# Server agent guide

## Scope

`server/` is a standalone CommonJS Express proxy package launched by the root `npm run start`. It is not a Nuxt/Nitro `server/api` directory.

## Files and behavior

| File | Role |
|---|---|
| `server/package.json` | package manifest |
| `server/package-lock.json` | dependency lock |
| `server/tsconfig.json` | TypeScript configuration stub |
| `server/tts-proxy.js` | runtime proxy on port 3500 |

Routes:

- `GET /proxy/elevenlabs/voices`
- `GET /proxy/elevenlabs/subscription`
- `POST /proxy/playht/stream`
- `GET /proxy/playht/voices`
- `GET /proxy/playht/cloned-voices`

## Constraints

- Do not silently move this code into Nitro; root startup and client callers depend on the standalone process.
- Do not log auth-bearing headers, credentials, full request bodies, or unredacted provider responses.
- The current broad CORS policy, raw upstream errors, hardcoded port, and client-supplied credentials are prototype behavior—not a production security model.
- Do not add robot, OBS, wallet, or platform privileges to this proxy. New privileged services belong behind the boundaries in `PLAN.md`.
- Keep root and server lockfiles consistent when dependencies change.

## Verification

Run `npm test` on Node.js 22 or later after a locked dependency install with lifecycle scripts disabled. The tests execute the actual proxy script in child processes on private Unix sockets with synthetic provider responses; no real provider or TCP listener is used. See `TESTING.md` for coverage, isolation and the dependency-update evidence. Syntax-check changed JavaScript as well.

## Changelog

- 2026-10-30: Replace the placeholder test guidance with the offline proxy/parser regression suite.
