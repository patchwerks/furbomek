# FurboMek Plan

## Goal
Turn FurboMek from a browser-only BIPCI conversation/TTS prototype into a safety-gated embodied agent platform:
- physical robot body attached to a manual human-operated control box today
- wireless bridge to virtualize that control path
- Hermes Agent running on a Minisforum UM773 Mini PC with Ubuntu as the planning/orchestration layer
- 24/7 livestream presence across PumpFun, Twitch, and optionally X
- real-time speech/chat reactions, internet interaction, and limited on-chain behavior
- local Forgejo as the source of truth now, with a later GitHub open-source release path

## Non-goals for v1
- No unrestricted raw LLM control of actuators
- No direct internet-facing actuator control
- No direct on-chain-to-motor control path
- No full robot autonomy before safe local control exists
- No public launch before operator override, audit logs, and failure handling are proven

## Current state
- `/Users/thales/dev/FurboMek` is currently a Nuxt 3 SPA plus a small Express TTS proxy
- `/Users/thales/dev/FurboMek/app.vue` is the main orchestration hotspot
- `/Users/thales/dev/FurboMek/src/settings.ts` contains BIPCI persona defaults and provider settings
- `/Users/thales/dev/FurboMek/server/tts-proxy.js` proxies ElevenLabs and PlayHT traffic on `localhost:3500`
- There is no current robot-control, firmware, sensor, actuator, social automation, or Solana-control stack in the repo

## Architectural principle
All external inputs produce **requested actions only**.

Only a **local safety controller** may approve and execute physical robot actions.

That means:
- Twitch chat does not move motors directly
- X/Twitter does not post without policy checks
- Solana events do not directly actuate hardware
- Hermes is the planner/orchestrator, not the final authority for physical movement

## Target architecture

### 1. Hardware interface layer
Purpose: abstract the current manual control box into a machine-readable and machine-writable control boundary.

Responsibilities:
- inspect and document the manual control box electrical/protocol model
- determine whether control is button-matrix, analog, serial, PWM, GPIO, custom PCB logic, or mixed
- capture safe neutral/default states
- define command timing, maximum rate, and legal ranges

Deliverables:
- wiring/protocol document
- safe command vocabulary (`MOVE_FORWARD`, `TURN_LEFT`, `STOP`, etc.)
- local hardware shim or microcontroller bridge

### 2. Wireless control bridge
Purpose: virtualize the human control box without removing manual control.

Requirements:
- preserve physical manual override
- local heartbeat/watchdog
- fail to neutral state on disconnect
- one-way authenticated control channel between UM773 and robot bridge

Likely implementation pattern:
- small dedicated bridge controller near the robot
- UM773 sends high-level commands over a constrained wireless link
- bridge translates them into safe control-box-equivalent signals

### 3. Local safety controller
Purpose: the only component allowed to authorize actuation.

Responsibilities:
- validate command allowlist
- enforce rate limits and motion envelopes
- enforce heartbeat and watchdog timeout
- reject conflicting or stale commands
- require explicit mode selection (`manual`, `operator-assisted`, `demo-autonomy`, `maintenance`)
- expose emergency stop and neutral-state fallback

Rules:
- network loss -> neutral state
- planner crash -> neutral state
- malformed command -> reject and log
- conflicting commands -> prioritize stop/neutral

### 4. Hermes control plane on Ubuntu (UM773)
Purpose: run the planning/orchestration stack on the Mini PC without making the model equivalent to root.

Responsibilities:
- observe local sensors/telemetry/status
- plan actions using the Hermes Agent
- call a narrow action broker instead of touching hardware directly
- supervise local services for robot control, streaming, social, and chain workers

Constraints:
- Hermes runs unprivileged
- privileged operations go through narrow broker services only
- service supervision via `systemd`
- break-glass operator access remains separate from the agent path

### 5. Operator plane
Purpose: preserve human authority.

Required controls:
- physical e-stop
- local stop/pause UI
- remote authenticated override
- manual mode forcing all autonomous requests to queue only
- incident mode disabling all outbound actions except operator-approved ones

### 6. Streaming plane
Purpose: make FurboMek continuously visible and interactive.

Surfaces:
- Twitch livestream
- PumpFun livestream/community presence
- optional X/Twitter clipping/posting

Capabilities:
- 24/7 camera and microphone streaming
- live TTS speech from agent outputs
- audience-response loop with moderation
- scene/state overlays showing mode, queue, wallet risk mode, and operator status

Rules:
- streaming must continue independently from robot motion where possible
- failure in posting/social/on-chain systems must not break the robot safety controller

### 7. Social and content plane
Purpose: convert agent reasoning into moderated, platform-safe public output.

Responsibilities:
- ingest Twitch chat, X mentions, and other audience signals
- maintain a content queue
- classify messages into: respond live, post later, ignore, escalate
- produce drafts first, then auto-post only for low-risk categories
- support operator review for higher-risk outputs

### 8. On-chain / Solana plane
Purpose: give FurboMek a bounded crypto-native presence.

Principles:
- separate treasury/control authorities from hot-wallet operations
- no direct treasury or admin-key exposure to Hermes
- hot wallet only for tightly capped operational actions
- token/community gating must be policy-driven, not direct motor authority

Potential uses:
- gated commands or queue eligibility
- community voting on non-safety-critical behaviors
- limited spend or reward actions
- public audit trail of selected events

Not allowed in early phases:
- direct on-chain-to-actuator control
- unrestricted token-holder control of motion
- full treasury control by the agent

## Safety boundaries

### Hard boundaries
- Physical movement authority stays local
- Public internet inputs are advisory, not authoritative
- Wallet privileges are split by risk level
- Streaming/social workers cannot call the hardware bridge directly

### Soft boundaries
- Hermes may propose actions, but broker/controller validates them
- Social and on-chain systems may enqueue requests, not execute them
- Operator may approve elevated actions explicitly

## Privilege model

### Process roles
- `hermes-planner`: unprivileged reasoning process
- `action-broker`: narrow privileged broker for approved verbs only
- `robot-bridge`: hardware/wireless bridge process
- `stream-worker`: OBS/capture/control worker
- `social-worker`: Twitch/X/PumpFun content worker
- `chain-worker`: Solana watcher/executor with capped hot-wallet powers
- `audit-writer`: append-only event log writer

### Key / credential roles
- read-only API credentials for ingestion
- posting credentials for social accounts
- capped hot wallet for low-risk on-chain actions
- multisig/cold custody for sensitive authorities
- distinct operator break-glass credentials

## Failure modes
- heartbeat lost between UM773 and bridge
- stream worker crashes during live session
- wallet provider/API rate limits hit
- social API ban/rate limit/moderation event
- Hermes outputs unsafe or nonsensical motion intent
- command queue floods from audience activity
- operator override path unavailable

Each must degrade safely.

## Required acceptance criteria by milestone

### Milestone 0 — Reality capture
Goal: document the existing robot/control-box/mechanical system.

Deliverables:
- hardware inventory
- control-box protocol/wiring map
- operator workflow video or sequence diagram
- current manual safety procedures

Acceptance:
- manual control path is documented end-to-end
- neutral state and e-stop behavior are explicit
- unknowns list exists with owners

### Milestone 1 — Wireless virtualization of manual control
Goal: replace direct human-only wiring dependency with a safe bridge while preserving manual override.

Deliverables:
- bridge controller design
- wireless command transport
- watchdog and heartbeat
- manual override preserved

Acceptance:
- when heartbeat is lost for defined timeout, robot enters neutral state
- manual override always defeats remote command stream
- invalid commands are rejected and logged

### Milestone 2 — UM773 local control stack
Goal: let Ubuntu supervise and command the bridge safely.

Deliverables:
- systemd-supervised services
- local dashboard or CLI for operator commands
- brokered action execution model
- telemetry/status surfaces

Acceptance:
- restart of planner does not leave robot moving
- operator can stop all motion through local control path
- service restart leaves bridge/controller in safe state

### Milestone 3 — Audio/chat embodiment
Goal: connect speech, STT, TTS, and character behavior to the embodied system.

Deliverables:
- migrate current BIPCI app behavior into a reusable local control UI or service layer
- voice/input/output routing suitable for the UM773 host
- stateful conversation handling

Acceptance:
- FurboMek can hear, think, and speak without requiring browser-only hacks for core control
- the speech path survives reconnects and device changes

### Milestone 4 — Streaming stack
Goal: 24/7 stream-capable operations.

Deliverables:
- persistent capture/streaming setup
- scene/overlay control
- reconnect/recovery logic
- moderation ingestion

Acceptance:
- 24-hour local soak test with no unrecovered crash in the streaming control stack
- stream can remain up while robot control is paused
- operator can mute/pause/stop stream independently

### Milestone 5 — Social/content pipeline
Goal: let FurboMek react publicly in a controlled way.

Deliverables:
- Twitch ingestion and response queue
- X/Twitter posting queue
- content drafting and moderation policy
- cooldowns/rate budgets

Acceptance:
- low-risk posts can auto-send under policy
- higher-risk posts route to operator review
- rate-limit failures trigger backoff and logging, not spam retries

### Milestone 6 — Solana control and identity
Goal: give FurboMek bounded on-chain agency.

Deliverables:
- hot-wallet policy
- multisig/cold authority split
- token/community gating rules
- on-chain event ingestion

Acceptance:
- no sensitive authority keys live on the planner host without explicit design signoff
- hot-wallet caps are enforced in code and ops policy
- on-chain signals can enqueue behavior changes but not directly actuate movement

### Milestone 7 — Hermes guarded autonomy
Goal: enable broad but bounded LLM-driven orchestration.

Deliverables:
- planner -> broker -> controller separation
- policy engine for action classes
- operator incident mode and break-glass flows
- append-only audit logs

Acceptance:
- every outbound action has an audit record
- every physical action is attributable to policy + request source
- incident mode blocks all non-essential outbound actions instantly

### Milestone 8 — Open-source hygiene
Goal: prepare for later GitHub publication.

Deliverables:
- secret-free repo
- `.env.example` and safe config templates
- hardware docs separated from sensitive deployment details
- license + contributor guidance

Acceptance:
- secret scan passes
- local Forgejo remains source of truth until release branch is ready
- public repo can be cloned without leaking keys, stream tokens, or unsafe control endpoints

## Suggested repo evolution

### New top-level areas likely needed later
- `docs/hardware/`
- `docs/ops/`
- `docs/security/`
- `services/` or `apps/` for broker/bridge/stream/social/chain workers
- `infra/` for UM773 provisioning and systemd units

## Decisions already made
- local Forgejo remains canonical for now
- GitHub open source is deferred
- nested duplicate repo is archived as backup at `/Users/thales/github/furbomek-code-backup`

## Must not build yet
- direct token-holder motor control
- direct model access to admin keys or treasury
- silent unrestricted posting bots
- 24/7 public autonomy without operator override and incident controls
- generalized “internet does anything” shell access for the model

## Immediate next steps
1. Capture the physical control-box protocol and safety model
2. Design the wireless bridge and local safety controller boundary
3. Define the Ubuntu/Hermes service topology on the UM773
4. Refactor current BIPCI app assumptions into components that can support the new embodied stack
5. Build the operator override and audit model before public automation or on-chain control
