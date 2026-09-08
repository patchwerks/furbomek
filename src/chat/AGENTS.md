# Chat integration agent guide

## Scope

`src/chat/` implements the current browser conversation abstraction and OpenAI Assistants adapter.

| File | Role |
|---|---|
| `abstractChat.ts` | event types and abstract conversation contract |
| `openai-assistant.ts` | thread/run lifecycle and streamed text adapter |

## Important behavior

- `OpenAIAssistantChat` owns a remote thread and at most one current streamed run.
- `preSend` creates a provisional user message; `send` reuses it when present.
- Starting a new run aborts the previous stream.
- Events `create`, `delta`, and `message` are consumed by the root application.

## Constraints

- Do not expose provider keys in browser builds or logs.
- Do not use this browser client as the Hermes/robot control plane.
- Preserve event ordering and cancellation behavior unless all consumers are updated together.
- The planned conversation service should translate model output into typed character/action requests; it must never emit raw actuator commands.

## Verification

Test provisional-message replacement, stream cancellation, empty/delta handling, thread cleanup, and provider failure paths. Run the root build after changes.
