# PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-16 11:12:02 MDT
**Commit:** 26676af
**Branch:** refactor/app.vue

## OVERVIEW
Current repo reality: browser-only Nuxt 3 app for BIPCI/FurboMek conversation + TTS orchestration, plus a small Express proxy for TTS vendors.
Not current repo reality: robot control, Furby hardware control, webcam/streaming control, autonomous trading, firmware, or actuator/sensor orchestration.

## CURRENT SOURCE OF TRUTH
- Canonical working tree: `/Users/thales/dev/FurboMek`
- Nested duplicate snapshot: `/Users/thales/dev/FurboMek/furbomek-code`
- Dependency authority: `/Users/thales/dev/FurboMek/package.json`, `/Users/thales/dev/FurboMek/package-lock.json`
- Nuxt config: `/Users/thales/dev/FurboMek/nuxt.config.ts`
- Runtime starts from root package scripts, not from the nested copy.

## STRUCTURE
```text
/Users/thales/dev/FurboMek/
├── app.vue                  # main UI/runtime orchestration hotspot
├── src/                     # client-side domain code
│   ├── chat/                # OpenAI assistant runtime
│   ├── tts/                 # ElevenLabs + PlayHT streaming logic
│   ├── types/               # shared TS interfaces
│   ├── settings.ts          # settings schema/defaults
│   └── settings.vue         # settings modal UI
├── server/                  # standalone Express TTS proxy package
├── public/                  # static assets only
├── furbomek-code/           # nested duplicate repo snapshot; ignore/quarantine
└── *.docx / swap / DS_Store # non-source artifacts
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Runtime boot | `/Users/thales/dev/FurboMek/package.json` | `start` runs Nuxt + proxy concurrently |
| Main UI flow | `/Users/thales/dev/FurboMek/app.vue` | 882-line orchestration file |
| App config | `/Users/thales/dev/FurboMek/nuxt.config.ts` | `ssr: false`, BootstrapVueNext, Nuxt ESLint |
| Client settings model | `/Users/thales/dev/FurboMek/src/settings.ts` | high-risk defaults / hardcoded keys |
| Assistant integration | `/Users/thales/dev/FurboMek/src/chat/openai-assistant.ts` | browser OpenAI client |
| TTS providers | `/Users/thales/dev/FurboMek/src/tts/` | audio streaming + proxy coupling |
| Proxy backend | `/Users/thales/dev/FurboMek/server/tts-proxy.js` | port `3500`, ElevenLabs/PlayHT forwarding |
| Type config | `/Users/thales/dev/FurboMek/tsconfig.json` | relaxed strictness despite Nuxt strict flag |

## CODE MAP
| Symbol/Area | Type | Location | Role |
|---|---|---|---|
| `app.vue` | root component | `/Users/thales/dev/FurboMek/app.vue` | owns chat/audio/device lifecycle |
| `Settings` | type/defaults | `/Users/thales/dev/FurboMek/src/settings.ts` | provider config schema |
| `OpenAIAssistantChat` | class | `/Users/thales/dev/FurboMek/src/chat/openai-assistant.ts` | OpenAI assistants client |
| `PlayHtTTS` / `PlayHtTTSStream` | classes | `/Users/thales/dev/FurboMek/src/tts/playht.ts` | PlayHT streaming via local proxy |
| `ElevenLabsTTS` / `ElevenLabsTTSStream` | classes | `/Users/thales/dev/FurboMek/src/tts/elevenlabs.ts` | ElevenLabs websocket streaming |
| `tts-proxy.js` | backend entrypoint | `/Users/thales/dev/FurboMek/server/tts-proxy.js` | credential-forwarding proxy |

## CONVENTIONS
- npm is the only evidenced package manager.
- Root app is ESM (`"type": "module"`), but proxy code is CommonJS.
- Nuxt config says `typescript.strict: true` and `typeCheck: true`; root `tsconfig.json` then relaxes several strict checks.
- Source imports commonly use `~/src/...` aliasing.
- `src/` is domain-oriented, not standard Nuxt pages/components/composables/stores layout.
- Provider configuration currently persists through local settings/UI rather than a clean env-only flow.

## ANTI-PATTERNS (THIS PROJECT)
- Do not treat `/Users/thales/dev/FurboMek/furbomek-code` as a second active workspace.
- Do not describe this repo as already containing robot-control or autonomy systems.
- Do not trust `README.md` as current operational truth; it is still the generic Nuxt starter.
- Do not copy or expose credentials from `/Users/thales/dev/FurboMek/src/settings.ts` into docs, commits, or logs.
- Do not assume “strict TypeScript” from Nuxt config means the repo is actually strict.

## UNIQUE STYLES
- `app.vue` contains many local composable-style functions inline instead of distributing them into `composables/`.
- TTS code mixes browser audio APIs, queueing, fetch/WebSocket flows, and local proxy assumptions.
- Chat behavior is constrained by the BIPCI prompt defaults in `src/settings.ts`.

## COMMANDS
```bash
npm install
npm run build
npm run generate
npm run preview
npm run start
```

Operational notes:
- `npm install` triggers `postinstall`, which runs `nuxt prepare`, `nuxt build`, and `cd server && npm install`.
- There is no root `dev`, `lint`, `test`, or `typecheck` script.
- `server/` proxy listens on `localhost:3500`.

## NOTES
- `furbomek-code/` is now gitignored as a nested duplicate snapshot.
- Current tree contains editor/OS artifacts (`.app.vue.swp`, `.DS_Store`) and a binary doc artifact (`ai prompt bipci.docx`).
- Use code over docs when they conflict.
