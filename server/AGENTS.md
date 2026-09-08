# SERVER KNOWLEDGE BASE

## OVERVIEW
`/Users/thales/dev/FurboMek/server` is a tiny but real backend boundary: a standalone Express proxy package used at runtime by the root app.

## STRUCTURE
| File | Role |
|---|---|
| `/Users/thales/dev/FurboMek/server/package.json` | package manifest |
| `/Users/thales/dev/FurboMek/server/package-lock.json` | server dependency lock |
| `/Users/thales/dev/FurboMek/server/tsconfig.json` | TS config stub extending Nuxt server tsconfig |
| `/Users/thales/dev/FurboMek/server/tts-proxy.js` | actual runtime proxy |

## RUNTIME ROLE
- Started by root `npm run start`.
- Listens on port `3500`.
- Proxies ElevenLabs and PlayHT API requests.
- Exists because the client app expects localhost proxy endpoints.

## ROUTES
- `GET /proxy/elevenlabs/voices`
- `GET /proxy/elevenlabs/subscription`
- `POST /proxy/playht/stream`
- `GET /proxy/playht/voices`
- `GET /proxy/playht/cloned-voices`

## CONVENTIONS
- CommonJS in a repo whose root package is ESM.
- Minimal Express + CORS package; no larger framework structure.
- Request headers are forwarded to upstream providers.

## ANTI-PATTERNS
- Do not assume this is a Nuxt/Nitro `server/api` directory. It is a separately launched Express process.
- Do not move routes into Nuxt server conventions without explicitly redesigning runtime startup.
- Do not expose auth-bearing headers or raw upstream errors in new logs.

## KNOWN HAZARDS
- Port `3500` is hardcoded.
- Upstream error messages are returned directly in failure cases.
- There is no meaningful server test setup; `npm test` is just the default placeholder.
- Root install/start scripts are tightly coupled to this folder.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Proxy behavior | `/Users/thales/dev/FurboMek/server/tts-proxy.js` | main backend logic |
| Runtime coupling | `/Users/thales/dev/FurboMek/package.json` | starts this process concurrently |
