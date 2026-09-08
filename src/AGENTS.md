# SRC KNOWLEDGE BASE

## OVERVIEW
`/Users/thales/dev/FurboMek/src` holds the real client-side domain code for BIPCI/FurboMek behavior.

## SUBSTRUCTURE
| Area | Location | Role |
|---|---|---|
| Settings model | `/Users/thales/dev/FurboMek/src/settings.ts` | schema/defaults for OpenAI, Deepgram, ElevenLabs, PlayHT |
| Settings UI | `/Users/thales/dev/FurboMek/src/settings.vue` | edits provider/runtime settings |
| Chat domain | `/Users/thales/dev/FurboMek/src/chat/` | event model + OpenAI assistants client |
| TTS domain | `/Users/thales/dev/FurboMek/src/tts/` | audio stream providers |
| Shared types | `/Users/thales/dev/FurboMek/src/types/` | interfaces only |

## WHAT IS UNUSUAL
- No `pages/`, `components/`, `composables/`, or `stores/` structure here.
- `settings.vue` is effectively a component but lives at `src/` root.
- `src/` modules are consumed by a monolithic `/Users/thales/dev/FurboMek/app.vue`.
- Local settings and provider behavior are tightly coupled.

## CENTRAL FILES
- `/Users/thales/dev/FurboMek/src/settings.ts`
- `/Users/thales/dev/FurboMek/src/settings.vue`
- `/Users/thales/dev/FurboMek/src/chat/openai-assistant.ts`
- `/Users/thales/dev/FurboMek/src/tts/interfaces.ts`

## CONVENTIONS
- Type imports are used heavily.
- Provider/service code is class-based.
- Several files use `*.interface.ts` naming.
- `~/src/...` alias imports are common.

## ANTI-PATTERNS
- Do not add more secrets/default credentials to `settings.ts`.
- Do not assume `src/` follows standard Nuxt app-directory conventions.
- Do not edit the nested duplicate under `/Users/thales/dev/FurboMek/furbomek-code/src/` when changing active code.

## KNOWN HAZARDS
- `settings.ts` contains apparent hardcoded API credentials/defaults.
- `settings.vue` imports `~/src/settings.js` while the source file is TypeScript.
- Browser runtime behavior depends on localStorage-persisted settings, audio device access, and provider network availability.
- `.DS_Store` exists under `src/` and is noise, not source.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Prompt/personality changes | `/Users/thales/dev/FurboMek/src/settings.ts` | BIPCI rules live here |
| Settings modal behavior | `/Users/thales/dev/FurboMek/src/settings.vue` | provider parameter UX |
| Assistant behavior | `/Users/thales/dev/FurboMek/src/chat/openai-assistant.ts` | OpenAI thread/run flow |
| Audio/TTS | `/Users/thales/dev/FurboMek/src/tts/` | most specialized code |
