# Client source agent guide

## Scope

`src/` contains the current browser-side domain code used by the monolithic root `app.vue`.

| Area | Role |
|---|---|
| `src/settings.ts` | provider/personality schema and safe blank defaults |
| `src/settings.vue` | settings modal |
| `src/chat/` | conversation event model and OpenAI Assistants client |
| `src/tts/` | ElevenLabs and PlayHT audio streaming |
| `src/types/` | shared browser interfaces |

## Conventions

- Existing code uses class-based provider integrations, type-only imports, and `~/src/...` aliases.
- `settings.vue` is a component despite living at `src/` root.
- This directory does not currently follow Nuxt `pages/`, `components/`, `composables/`, or `stores/` conventions.
- Provider behavior and browser-persisted settings are tightly coupled to `app.vue`.

## Constraints

- Never add secrets or usable default credentials to `src/settings.ts`; browser code is not a secret boundary.
- Treat `dangerouslyAllowBrowser` in `src/chat/openai-assistant.ts` as migration debt, not precedent.
- Do not put physical motion, serial, OBS, social-account, or wallet privileges in client code.
- Preserve event names and audio ordering when changing provider implementations.
- New cross-process contracts should be schema-driven packages as described in `PLAN.md`, not ad hoc browser globals.

## Verification

Run `npm run build` for type/build validation. Exercise microphone, output-device selection, interruption, reconnect, and both TTS providers when touching their lifecycle code.
