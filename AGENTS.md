# Furb-o-Mek agent guide

## Repository purpose

This repository is the source of truth for Furb-o-Mek: an offboard Hermes-controlled, fully autonomous streaming robot built around a modified Freenove-style hexapod and Furby-like head mechanism.

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
├── assets/models/furbomek/   # editable character sources, game exports, scene, provenance
├── .schematics/             # photo-derived labelled blueprint sheets
├── docs/
│   ├── research/          # evergreen topic evidence plus dated syntheses
│   └── operations/        # exact deployment, recovery and incident procedures
├── FUNDING.md               # public-safe, dated bench-tool baskets and measurement gates
├── HERMES.md                # fresh-clone host-Hermes deployment entrypoint
├── package.json             # root scripts and dependency authority
├── PLAN.md                  # architecture, evidence, milestones and gates
└── AGENTS.md                # this file
```

Directory-specific guidance exists in `server/AGENTS.md`, `src/AGENTS.md`, `src/chat/AGENTS.md`, and `src/tts/AGENTS.md`.

For character assets, read [`assets/models/furbomek/AGENTS.md`](assets/models/furbomek/AGENTS.md) and its README. This pack is visual source material, not a completed Phase 5 avatar integration or verified hardware model.

## Source of truth and evidence rules

- Use current code over the generic Nuxt `README.md` when they conflict.
- Treat hardware identifications in `PLAN.md` as inferred until confirmed in `docs/hardware/` by model/board markings, measurements, or firmware.
- Treat `.schematics/` as navigation and planning aids, never as verified fabrication or wiring drawings.
- Read `.schematics/README.md` and the paired sheet note before changing a hardware, audio, camera, or control-path claim.
- Read `docs/research/README.md` and the relevant topic note before adopting or replacing an external project, protocol, model, renderer, speech engine, browser worker, or agent framework.
- Preserve the distinction between current implementation and planned architecture.
- Prefer repo-relative paths in documentation so clones remain portable.
- Cite primary vendor/project documentation for hardware, protocols, platform APIs, and deployment claims.
- Do not copy third-party firmware until its license is reviewed. Freenove's upstream FNK0031 resources are non-commercial CC BY-NC-SA 3.0.
- Use explicit evidence labels: **observed**, **measured**, **reference/inferred**, **patent-described**, **proposed**, or **TBD**. Do not promote an inferred chipset, Furby generation, speaker rating, camera fit, or radio range to fact.
- Keep generation-specific evidence separate: a 1998 patent, 2005 mechanism, 2012 teardown, or Connect teardown applies only to the generation it documents.
- Funding prices require access dates, price/stock/tax/shipping caveats, and a PII scan.

## Autonomous runtime topology

- Normal operation is untethered from both the handheld movement remote and the yellow facial-control box. Neither retains external cable or runtime authority.
- No person operates a legacy button or speed knob during runtime. Legacy inputs may be characterized and then emulated electrically.
- The yellow box may be removed after reverse-engineering. A useful PCB may remain only if mounted inside the robot and driven through a measured, protected interface.
- “Isolated microcontroller gateway” means a **physical robot-mounted** MCU, robot-side radio, independent watchdog, power conditioning, and isolation/level/driver board.
- The robot-mounted gateway is distinct from the offboard Linux embodiment-gateway service. The offboard service applies semantic policy; the robot-mounted MCU owns final TTL expiry, interlocks, and stop behavior.
- The current external OBS camera is the near-term vision source. Embedded eye/forehead cameras and 1–3 mile links are gated proposals, not established capabilities.
- Factory-speaker reuse is TBD until its label, conductors, DC resistance/impedance, rating, and drive topology are measured.

## Runtime UI, avatar, and OS boundaries

- Read `docs/research/runtime-ui-stack-2026-09-21.md` before changing A2UI, AIRI/avatar, OBS, OpenGolem/swarm, Hermes-adapter, or Omarchy decisions.
- Hermes is the sole character/planning authority. A project-owned broker owns character/HUD state; browser sources and avatar renderers never receive Hermes keys or tools.
- `patchwerks/jabberwerk` is the canonical STT/TTS/STS/voice/DSP plane. Furb-o-Mek and AIRI consume its capability/profile/timeline contracts and do not grow parallel engine-specific speech stacks.
- A2UI is a constrained presentation format, not an OBS controller or action surface. Keep protocol and package versions as separate pins and default to a read-only reduced catalog.
- Avatar implementations are adapters behind one project contract. AIRI is a renderer by default, a scoped capability service when possible, and an isolated A2A specialist only when its own agent loop is genuinely required.
- A2A carries tasks/status/artifacts, not PCM, visemes, frame animation, OBS commands, or robot motion.
- Omarchy is a full Arch/Hyprland OS. Run it as a full VM or bare-metal profile, never describe it as an Ubuntu container layer.
- OpenGolem-style workers are advisory task-plane producers only. Exclude anti-detection, account-concealment/purchasing, proxy-rotation, synthetic-human timing, and engagement-manipulation material.

## Security and physical-safety invariants

- Never commit credentials, tokens, stream keys, wallet secrets, device identifiers, or private endpoints.
- Never restore the previously removed default provider credentials in `src/settings.ts`.
- Never expose arbitrary serial, GPIO, shell, OBS, or wallet access to Hermes.
- Public/community/on-chain input may request behavior but cannot directly actuate hardware.
- Every motion command must be bounded by TTL, allowlist, rate, mode, and local watchdog.
- `STOP` must be local, unconditional, idempotent, and higher priority than all other actions.
- Radio/process/interface/heartbeat loss must stop gait and release both head directions locally.
- Head forward/reverse commands require electrical and firmware interlocks; boot/reset defaults are inactive.
- Do not connect the Furby head controller to MCU pins until voltages and signal behavior are measured.
- Hardware tests require physical support for the robot and an independent actuator power cut.
- Never select final head driver, fuse, battery, speaker amplifier, or camera mount before the dependent measurements are recorded.

## Current commands

```bash
npm ci
npm run build
npm run generate
npm run preview
npm run start
```

Notes:

- `npm ci` invokes `postinstall`, which builds Nuxt and installs `server/` dependencies.
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
7. For documentation changes, validate relative links and SVG XML/rendering, then scan staged public text for secrets and PII.
8. Preserve `HERMES.md` and `docs/operations/hermes-one-shot.md` as honest end-to-end entrypoints: never document a command as runnable before it exists and passes its stated gate.
