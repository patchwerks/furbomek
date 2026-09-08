# TTS KNOWLEDGE BASE

## OVERVIEW
`/Users/thales/dev/FurboMek/src/tts` is the most specialized client code: audio playback, streaming, provider auth headers, and local proxy coupling.

## FILE MAP
| File | Role |
|---|---|
| `/Users/thales/dev/FurboMek/src/tts/interfaces.ts` | provider/stream contracts |
| `/Users/thales/dev/FurboMek/src/tts/elevenlabs.ts` | websocket streaming TTS |
| `/Users/thales/dev/FurboMek/src/tts/playht.ts` | fetch/stream proxy-based TTS |

## CONVENTIONS
- Providers implement `TTSInterface`.
- Stream classes extend `EventTarget`.
- Browser `AudioContext` scheduling is handled manually.
- Audio output switching uses `setSinkId` typing from `/Users/thales/dev/FurboMek/src/types/audio-context.interface.ts`.

## MUST VERIFY BEFORE EDITING
- Whether a provider uses direct upstream WebSocket/fetch or the local proxy.
- Whether changes affect event names: `first`, `last`, `send`, `outOfCredits`.
- Whether local playback timing depends on queued audio chunk ordering.

## ANTI-PATTERNS
- Do not remove the localhost proxy assumption casually; root runtime depends on `server/tts-proxy.js` at port `3500`.
- Do not treat ElevenLabs and PlayHT flows as interchangeable; one is direct websocket-heavy, one is proxy/fetch-heavy.
- Do not add more debug logging with request/auth detail.

## KNOWN HAZARDS
- `playht.ts` uses `any`, non-null assertions, and manual queue/reader state.
- `elevenlabs.ts` contains browser-side provider key usage and manual PCM decoding.
- Both implementations assume browser audio APIs and may break outside a client-only runtime.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Shared provider contract | `/Users/thales/dev/FurboMek/src/tts/interfaces.ts` | start here for API changes |
| ElevenLabs logic | `/Users/thales/dev/FurboMek/src/tts/elevenlabs.ts` | WebSocket + AudioContext |
| PlayHT logic | `/Users/thales/dev/FurboMek/src/tts/playht.ts` | localhost proxy + stream queue |
