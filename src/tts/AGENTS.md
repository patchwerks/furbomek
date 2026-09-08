# TTS agent guide

## Scope

`src/tts/` contains the specialized browser audio providers, stream queues, output-device routing, and current proxy coupling.

| File | Role |
|---|---|
| `interfaces.ts` | provider and stream contracts |
| `elevenlabs.ts` | ElevenLabs WebSocket/audio path |
| `playht.ts` | PlayHT proxy/fetch stream and queue |

## Preserve when editing

- Provider event semantics, including `first`, `last`, `send`, and `outOfCredits`.
- Audio chunk order and interruption behavior.
- `AudioContext` scheduling and output selection via `setSinkId` typing in `src/types/audio-context.interface.ts`.
- The distinction between the direct WebSocket-heavy ElevenLabs flow and proxy/fetch-heavy PlayHT flow.

## Constraints

- Do not log keys, auth headers, raw credentials, or sensitive provider responses.
- Do not assume the localhost proxy can be removed without updating root startup and all callers.
- Do not add actuator calls here. Emit time-aligned speech/viseme/energy events for a separate character-state service.
- Manual `any`, non-null assertions, and queue state in `playht.ts` are known hazards; add focused tests before refactoring.

## Verification

Test first audio, chunk ordering, forced flush, normal end, interruption, provider disconnect, output-device changes, and cleanup. Run `npm run build` after changes.
