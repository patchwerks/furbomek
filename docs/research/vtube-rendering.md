# VTuber rendering and AI-streamer references

Reviewed: 2026-09-21

## Selected architecture

Use a renderer-neutral `avatar-host` and character-event contract. Hermes owns the character and plans; jabberWERK owns speech/audio; the renderer owns pixels, expressions and motion; OBS owns composition.

Preferred order:

1. AIRI Stage Web adapter when no finished native rig exists.
2. Inochi Session when a project-owned Inochi2D model is ready.
3. Static project-owned avatar as guaranteed fallback.
4. OpenVT as a later Linux/Live2D engineering option.
5. VTube Studio only as a Mac/Windows compatibility option.

## Primary candidates

| Project | Evidence and useful parts | Decision |
|---|---|---|
| [AIRI](https://github.com/moeru-ai/airi) | Active character platform; web/Electron stages, Live2D/VRM/MMD/Tachie packages, audio/lip-sync packages, plugin/server transports and separate game integrations | Selected first renderer/capability research target, pinned and isolated |
| [Inochi Session](https://inochi2d.com/download/) | Open native VTubing runtime with Linux downloads; official player for Inochi2D models | Selected when a compatible licensed model exists |
| [OpenVT](https://github.com/erodozer/open-vt) | Linux-focused Godot/Live2D software, transparent-window support, VTube Studio model compatibility goal | Later candidate; build/submodules and Cubism licensing increase setup cost |
| [Live2D Cubism](https://www.live2d.com/en/) | Industry-standard 2D rig/editor/runtime ecosystem | Model format/tool reference, not an open runtime license blanket |
| [VTube Studio](https://github.com/DenchiSoft/VTubeStudio/wiki/FAQ/d5e37702314dd984680d2bfde2834e293f1e079e) | Mature tracking/Live2D application | Not the Omarchy default because Linux is officially unsupported |
| [VSeeFace](https://www.vseeface.icu/) | Strong VRM/VSFavatar tracking/rendering reference | Useful feature reference; not selected as the Linux autonomous host |
| [Animaze](https://www.animaze.us/allproducts) | Commercial avatar products and streaming UX | Product/UX reference only; no project-owned runtime boundary |
| [HoloWorld AVA Studio](https://docs.holoworld.com/holoworld/ava-studio) | Agentic scripted video/scene production | Reference for offline/short-form scene generation, not the realtime avatar core |

Live2D Cubism Core remains proprietary even where surrounding framework code is open ([official Core license notice](https://github.com/Live2D/CubismNativeSamples/blob/develop/Core/LICENSE.md)). Record model, SDK/Core and redistribution/streaming terms separately.

## AIRI boundary

AIRI is not reduced to “only pixels.” The integration has three optional layers:

- renderer consumer for Stage/models/motions;
- direct capability services for Minecraft, Factorio and other reusable bridges;
- scoped A2A specialist only when AIRI's cognitive loop is essential.

See [`agent-interoperability-a2a.md`](agent-interoperability-a2a.md). AIRI's STT/TTS provider layer is disabled by default in favor of [`voice-and-speech.md`](voice-and-speech.md).

## Reference implementations from the legacy notes

These projects are idea/code sources, not dependencies selected for production:

| Project | Pattern worth studying | Caution |
|---|---|---|
| [kimjammer/Neuro](https://github.com/kimjammer/Neuro) | Realtime STT/TTS, VTube Studio hotkeys, Twitch chat, multimodal screenshot loop, frontend signals | Seven-day experimental Python/Windows stack; weak moderation warning; duplicates Hermes/Jabberwerk |
| [z-waif](https://github.com/SugarcaneDefender/z-waif) | Local companion/VTuber architecture and game-oriented autonomy | Review exact license, maintenance, authority and Linux behavior before reuse |
| [Amica](https://github.com/semperai/amica) | Web-based interactive 3D character, VRM, speech synthesis/recognition and WebXR | Reference renderer/UX; avoid duplicating speech/agent authority |
| [elizaOS](https://github.com/elizaOS/eliza) | Broad platform adapters and agent integration patterns | Reference/port adapters selectively; do not introduce a second character brain |
| [AI-Waifu-Vtuber](https://github.com/ardha27/AI-Waifu-Vtuber) | Twitch integration patterns | Inspect API policy/currentness before borrowing |
| [AIVTuber](https://github.com/InsanityLabs/AIVTuber) | UI/UX and Live2D integration ideas | Model/provider-specific experimental stack |
| [vixevia](https://github.com/IRedDragonICY/vixevia) | Gemini-driven VTuber interaction design | Architecture reference only |
| [Open-LLM-VTuber-Lab](https://github.com/t41372/Open-LLM-VTuber) | Historical branches/experiments | Link now redirects to a lab/archive; find the current upstream before reuse |
| [Streamer-Sales](https://github.com/PeterH0323/Streamer-Sales) | ASR/TTS, digital-human frontend, RAG, FastAPI/Vue and Compose packaging | Commerce-specific, large integrated stack; mine patterns rather than importing wholesale |

The legacy notes also name `AvatarAI`, `MoltStream`, `Wallie V2`, `SendKit`, `talk2avatar`, `Persona`, `Anima`, and `Khavee SDK` without stable source URLs. They remain **unknown/unverified** until an exact repository/product URL, license, revision and current behavior are recorded.

## Hermes-specific avatar claims requiring rejection or revalidation

- `hermes-embodiment`: the cited repository could not be resolved during the prior review. Do not claim it is production-ready without a source.
- [`hermes-waifu`](https://github.com/waifuai/hermes-waifu): requires checkout/entrypoint integration and CDN/model assumptions; not a no-code production boundary.
- `omnilimb-face`: treat the PyPI/plugin claim as an unaudited candidate. Hermes plugins execute with broad agent privilege, so isolate and audit before any experiment.

These may inform prototypes, but the durable seam is the project-owned character broker and renderer adapter.

## Renderer contract

Every adapter implements:

```text
health
capabilities
load_character(asset_id)
apply_snapshot(character_state)
apply_event(seq, ttl, kind, payload)
set_visible
shutdown
```

Required properties:

- no Hermes, Jabberwerk, OBS, wallet, social or robot credentials;
- model/asset provenance and exact checksums;
- transparent or keyed OBS capture;
- deterministic snapshot recovery and stale-event rejection;
- timestamped PCM/viseme consumption from Jabberwerk;
- static fallback when the renderer lease expires;
- renderer failure cannot stop speech, stream director, Hermes or robot safety.

## Acceptance evidence

- 10-minute transparent/keyed capture at target resolution/FPS;
- real Hermes state change visible in under the target latency;
- audible Jabberwerk speech with measured audio/mouth skew;
- expression/state snapshot restored after process and Browser Source reload;
- stale, duplicate and cancelled utterances do not animate;
- 30-minute tracer-bullet soak and later 24-hour private soak;
- complete model/runtime license and redistribution record.
