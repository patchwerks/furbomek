# Agent swarms, browser/computer use and tool references

Reviewed: 2026-09-21

## Architectural decision

OpenGolem is a research vocabulary and source inventory, not a runtime selected for Furb-o-Mek. Hermes remains the top-level agent. Same-Hermes parallel work uses native delegation/Kanban/Bot Mode; cross-framework specialists use A2A only after capability and security gates.

Every worker is advisory by default. It receives a distinct identity, scoped credentials, network/filesystem policy, task/delegation/cost limits, replay protection, cancellation, tracing and circuit breaker. No worker directly controls the robot, OBS, wallets, social posting, firmware or mutable safety policy.

## Browser and computer-use references

| Source | Useful pattern | Decision |
|---|---|---|
| [Vercel agent-browser](https://github.com/vercel-labs/agent-browser) | Token-efficient CLI/browser primitives designed for agents | Candidate browser backend; sandbox, exact-session and policy evaluation required |
| [Hyperbrowser examples / Hypergraph](https://github.com/hyperbrowserai/hyperbrowser-app-examples/tree/main/hypergraph) | Traversable technical/skill graph and managed browser examples | UI/knowledge-graph reference; managed browser service requires explicit egress/data decision |
| [HyperAgent](https://github.com/hyperbrowserai/HyperAgent) | Multi-page agent browser, provider abstraction and MCP client | Reference implementation; avoid importing a second planner into Hermes |
| [OAGI Lux SDK](https://github.com/agiopen-org/oagi-python) | Computer-use model/desktop automation, including Wayland guidance | Candidate isolated computer-use worker, never direct host/robot authority |
| [Gradio detection viewer](https://github.com/hysts/gradio-detection-viewer) | Human-readable visual-model evaluation UI | QA/reference only |

Browser workers receive a disposable profile or explicitly selected session, URL allowlist, download/upload policy, time/action budgets and sanitized outputs. Their activity becomes HUD events through the broker; the A2UI page never becomes the controller.

## Deployment/orchestration references

[Docker Swarm](https://docs.docker.com/engine/swarm/) is infrastructure orchestration: desired service state, scaling, service discovery, overlay networking, mTLS and rolling updates. It is **not** an AI-agent swarm design. Furb-o-Mek starts with one host/VM and OCI/systemd services; adopt Docker Swarm only when multi-host service orchestration itself becomes necessary.

[Agno](https://github.com/agno-agi) and other agent frameworks are useful comparisons for teams, tools, memory and deployed control planes. They are not adopted as a second agent runtime while Hermes already supplies orchestration.

The legacy `deeperhermes`/Pinokio link refers to a separate self-reflective model/launcher project, not the maintained Nous Research Hermes Agent runtime. It is not a host-harness dependency for Furb-o-Mek.

## OpenClaw skills and marketplaces

The supplied note links to a large community skills collection and examples for collaboration, autonomy, task management, social posting and marketplaces. These are untrusted third-party instruction bundles, not dependencies.

Pointers reviewed or attempted:

- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills?tab=readme-ov-file#agent-to-agent-protocols)
- [AdaptlyPost skill](https://github.com/openclaw/skills/blob/main/skills/tarasshyn/adaptlypost/SKILL.md)
- [Siftly](https://github.com/viperrcrypto/Siftly)
- `aetherlang`, `agent-collaboration-network`, `agent-network`, `agent-weave`, `agentx-marketplace`
- `agent-autonomy-kit`, `adaptive-reasoning`, `agent-autopilot`, `agent-task-manager`
- [Agno PAL pointer](https://github.com/agno-agi/pal)

Several individual GitHub skill links did not render through the available reader. They remain unverified pointers; do not copy or install them without reading the exact source, commit, dependencies, network calls and license.

The AdaptlyPost example is a SaaS posting API with an API key and immediate/scheduled publishing. It is relevant only as a platform-adapter shape. Any posting operation remains a deterministic, separately credentialed community adapter with explicit policy, moderation, rate limits and audit. A skill prompt cannot grant posting authority.

Agent marketplaces, paid delegation, L402/x402 and wallet-linked capabilities are out of scope until wallet custody, budgets, counterparty identity, replay/idempotency and approval policy are designed separately.

## Data/social/market-intelligence pointers

| Source | Potential use | Status |
|---|---|---|
| [Siftly](https://github.com/viperrcrypto/Siftly) | Local organization and mind-map visualization of X bookmarks | Candidate local research UX |
| [Protokols API](https://docs.protokols.io/api-17192530) | Public profile/statistics data | Candidate data adapter; verify terms, auth and fields |
| Nansen skill search | Wallet/on-chain analysis | Exact skill/source was not retrievable; unknown |

Data adapters may feed public-safe HUD summaries. They do not receive wallet signing keys and cannot transact merely because they can analyze an address.

## VTuber/agent reference set

The OpenGolem note's VTuber repositories are catalogued in [`vtube-rendering.md`](vtube-rendering.md). Their useful patterns include Twitch integration, VRM/WebXR, frontend UX, realtime STT/TTS, RAG and digital-human deployment. Their agent loops are not adopted wholesale.

## Explicitly rejected material

The legacy OpenGolem note includes anti-detection and coordinated-account guidance. The following are excluded from research-to-implementation transfer:

- bought/borrowed/aged account acquisition;
- concealment of wallet/account associations;
- residential/mobile proxy rotation to evade detection;
- fingerprint/stealth browser use for policy evasion;
- synthetic-human delays/personas intended to bypass platform enforcement;
- account farms, coordinated engagement, mass posting/following/DMs;
- automated “poke” or other engagement manipulation.

Supported platform APIs and disclosed identities are the production boundary. Browser automation is never used to defeat a platform control.

## Candidate promotion checklist

Before a tool enters the architecture:

1. exact repository/release/commit and license recorded;
2. source and install scripts reviewed as untrusted;
3. secrets, telemetry, egress and update behavior documented;
4. capability narrowed to a project-owned schema;
5. isolated runtime and credentials;
6. failure, cancellation, replay and idempotency tested;
7. output treated as untrusted proposal/data;
8. no path to robot, OBS, wallet or social side effects outside deterministic policy;
9. value exceeds Hermes-native functionality and maintenance cost.
