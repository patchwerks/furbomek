# Furb-o-Mek agent guide

## Repository purpose

This repository is the source of truth for Furb-o-Mek: an offboard Hermes-controlled, autonomous streaming robot built around a modified Freenove-style hexapod and Furby head.

Current reality is much smaller than the target architecture. The checked-in application is a client-only Nuxt 3 conversation/TTS prototype plus a standalone Express TTS proxy. There is no robot firmware, gateway, OBS worker, perception service, social adapter, or deployment stack yet. Read `PLAN.md` before introducing those systems.

## Current map

```text
.
├── app.vue                  # main UI and browser orchestration hotspot
├── src/
│   ├── chat/                # current OpenAI Assistants client
│   ├── tts/                 # ElevenLabs and PlayHT streaming clients
│   ├── types/               # shared browser-side interfaces
│   ├── settings.ts          # settings schema and safe blank defaults
│   └── settings.vue         # settings UI
├── server/                  # separately launched CommonJS Express proxy
├── public/                  # static assets
├── .schematics/             # photo-derived labelled blueprint sheets
├── package.json             # root scripts and dependency authority
├── PLAN.md                  # architecture, evidence, milestones and gates
└── AGENTS.md                # this file
```

Directory-specific guidance exists in `server/AGENTS.md`, `src/AGENTS.md`, `src/chat/AGENTS.md`, and `src/tts/AGENTS.md`.

## Source of truth and evidence rules

- Use current code over the generic Nuxt `README.md` when they conflict.
- Treat hardware identifications in `PLAN.md` as inferred until confirmed in `docs/hardware/` by model/board markings, measurements, or firmware.
- Treat `.schematics/` as navigation and planning aids, never as verified fabrication or wiring drawings.
- Preserve the distinction between current implementation and planned architecture.
- Prefer repo-relative paths in documentation so clones remain portable.
- Cite primary vendor/project documentation for hardware, protocols, platform APIs, and deployment claims.
- Do not copy third-party firmware until its license is reviewed. Freenove's upstream FNK0031 resources are non-commercial CC BY-NC-SA 3.0.

## Security and physical-safety invariants

- Never commit credentials, tokens, stream keys, wallet secrets, device identifiers, or private endpoints.
- Never restore the previously removed default provider credentials in `src/settings.ts`.
- Never expose arbitrary serial, GPIO, shell, OBS, or wallet access to Hermes.
- Public/community/on-chain input may request behavior but cannot directly actuate hardware.
- Every motion command must be bounded by TTL, allowlist, rate, mode, and local watchdog.
- `STOP` must be local, unconditional, idempotent, and higher priority than all other actions.
- Do not connect the Furby head controller to MCU pins until voltages and signal behavior are measured.
- Hardware tests require physical support for the robot and an independent actuator power cut.

## Current commands

```bash
npm install
npm run build
npm run generate
npm run preview
npm run start
```

Notes:

- `npm install` invokes `postinstall`, which builds Nuxt and installs `server/` dependencies.
- There is no root `dev`, `test`, or dedicated `typecheck` script.
- `npm run start` launches the proxy and Nuxt concurrently.
- The proxy listens on localhost port 3500.

## Conventions

- npm/package-lock is the evidenced package-manager path.
- Root code is ESM; `server/tts-proxy.js` is CommonJS.
- Existing imports commonly use `~/src/...`.
- The present `src/` layout is domain-oriented rather than standard Nuxt pages/components/composables.
- New services must not be hidden inside `app.vue`; follow the target monorepo boundaries in `PLAN.md`.
- Add contract tests before connecting new commands to physical hardware.

## High-risk hotspots

| Area | Why it matters |
|---|---|
| `app.vue` | Large browser orchestration hotspot owning chat/audio/device lifecycle |
| `src/settings.ts` | Provider schema, personality prompt, and historic credential risk |
| `src/chat/openai-assistant.ts` | Uses `dangerouslyAllowBrowser`; not a privileged backend boundary |
| `src/tts/` | Browser audio timing and provider-specific streaming behavior |
| `server/tts-proxy.js` | Forwards auth-bearing headers and returns raw upstream errors |

## Change checklist

Before committing:

1. Confirm the change matches the current milestone in `PLAN.md`.
2. Check for secrets and generated/binary artifacts.
3. Run the relevant build/type/test commands that exist for the changed area.
4. For protocol changes, test simulator and hardware adapters against the same schema.
5. For hardware changes, document measured voltage, pin, firmware version, and safe failure behavior.
6. Update the nearest `AGENTS.md` when a directory's role or conventions materially change.
