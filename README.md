# Furb-o-Mek

Furb-o-Mek is a planned fully autonomous Hermes-controlled streaming robot built around a modified Freenove-style hexapod and Furby-like head. The target system combines safe remote embodiment, speech, an autonomous OBS stream, a swappable VTuber fallback, visual/perception overlays and future advisory agents.

## Start here

- Humans and coding agents: [`AGENTS.md`](AGENTS.md), then [`PLAN.md`](PLAN.md).
- A host Hermes deploying a fresh clone: [`HERMES.md`](HERMES.md).
- Exact current and target deployment flow: [`docs/operations/hermes-one-shot.md`](docs/operations/hermes-one-shot.md).
- Source-backed topic research: [`docs/research/README.md`](docs/research/README.md).
- Hardware/visual evidence: [`.schematics/README.md`](.schematics/README.md).
- Current hardware/firmware records: [`docs/hardware/README.md`](docs/hardware/README.md).
- Downloaded official manuals and schematics: [`Freenove archive`](docs/hardware/vendor/freenove/INDEX.md).
- Tested actuator-disabled safety component: [`firmware/robot-safety/README.md`](firmware/robot-safety/README.md).
- Bounded supported Hermes robot control: [`docs/operations/hermes-robot.md`](docs/operations/hermes-robot.md).
- Public activity and private media lifecycle: [`services/hermes-activity`](services/hermes-activity/README.md), [`services/stream-supervisor`](services/stream-supervisor/README.md).
- Non-live media verification: `bash tools/verify-media.sh`.

## Current status

The legacy browser application remains a Nuxt conversation/TTS prototype plus an Express proxy. Separately, the installed guarded USB/RF path completed eight bounded actions through actual Hermes on the supported operator-present bench. The STOP requester-ACK correction is software-tested but not yet installed. The independent actuator-disabled diagnostic remains separate from installed motion firmware.

The project also implements native Kinect/tracking/Godot presentation, a redacted Hermes activity observer/broker, locked private media-session supervision and non-live interface tests. Desktop screenshot publication remains unqualified and rejected; text/timeline activity does not require it. Exact deployment/private acceptance is recorded in [`media integration`](docs/operations/media-integration-2026-10-19.md). Floor/autonomous motion, the complete character bus, jabberWERK integration, avatar fallback, physical-head control and full unattended deployment remain separate gates.

Do not interpret a successful web build as autonomous-robot readiness.

## Current app

Use the committed npm lockfile:

```bash
npm ci
npm run build
npm run start
```

`npm ci` runs the root `postinstall`, which prepares/builds Nuxt and installs the nested `server/` dependencies. There is currently no root `dev` or test script.

Never commit `.env` files, provider keys, stream keys, wallet secrets, private voice artifacts, device identifiers or runtime logs.

## Architecture commitments

- Hermes is the single character/planning/tool authority.
- [`patchwerks/jabberwerk`](https://github.com/patchwerks/jabberwerk) is the intended speech/media plane.
- AIRI/Inochi/OpenVT are swappable renderer/capability integrations, not robot-safety authorities.
- A2UI is a constrained read-only OBS HUD format, not a control surface.
- Every physical command passes deterministic policy and a robot-mounted watchdog/interlock gateway.
- `STOP` is local, unconditional and higher priority than every model or service.

See [`PLAN.md`](PLAN.md) for implementation phases and acceptance gates.
