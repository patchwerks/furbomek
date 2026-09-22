# A2UI, OBS overlays and visual workers

Reviewed: 2026-09-21

## Decision

Use A2UI as a constrained declarative payload inside one project-owned OBS Browser Source. A2UI does not control OBS, execute tools or decide what data is public.

Pinned evaluation:

- A2UI source commit `9263942b373d01cc21ffd2fd9894bda43d9c7080`;
- protocol `v0.9.1` (current); `v1.0` remains a candidate;
- `@a2ui/web_core` 0.11.0;
- `@a2ui/lit` 0.11.0 through its `/v0_9` export.

Sources: [official roadmap](https://a2ui.org/roadmap/), [pinned protocol](https://github.com/a2ui-project/a2ui/blob/9263942b373d01cc21ffd2fd9894bda43d9c7080/specification/v0_9_1/docs/a2ui_protocol.md), [pinned Lit manifest](https://github.com/a2ui-project/a2ui/blob/9263942b373d01cc21ffd2fd9894bda43d9c7080/renderers/lit/package.json).

Protocol and package versions are independent; `v0.91.0` is not the protocol version.

## Ownership boundary

| Owner | Responsibilities |
|---|---|
| Hermes adapter | Translates run/tool/task lifecycle into public-safe activity events |
| Character/HUD broker | Redaction, classification, sequence, TTL, cancellation, snapshot/replay and consumer health |
| A2UI renderer | Maps approved data/components into project-native visual widgets |
| Overlay host | Fixed slots, typography, theme, effects, bounds, CSP, media proxy and stale states |
| Stream director | OBS WebSocket authentication, scene/source lifecycle, failover and reconciliation |
| OBS | Final source transform, z-order, viewport, program output and encoder |

The HUD displays safe activity summaries, never hidden chain-of-thought, prompts, cookies, private form fields, seed phrases, credentials or unredacted tool/database output.

## Reduced catalog

Allow initially:

- bundled icon and status badge;
- bounded text/caption;
- progress/status;
- key/value and bounded list;
- project-rendered sparkline from supplied numbers;
- same-origin/proxied image;
- normalized vision boxes/masks.

Disable initially:

- inputs and form submission;
- client functions/actions;
- arbitrary Markdown/HTML/CSS/JavaScript/shaders;
- iframe and remote asset URL;
- outbound links;
- free coordinates or source names;
- every Hermes, OBS, wallet, social or robot action.

Initial ceilings are documented in `PLAN.md`: 64 KiB/delta, 256 KiB/snapshot, 128 components, depth 12, 2,000 visible characters/component and 10 deltas/second/producer. Treat these as versioned policy, not library defaults.

## OBS behavior

OBS Browser Source can unload when hidden and refresh when a scene becomes active. State must therefore live outside the page and restore from a complete snapshot ([official Browser Source guide](https://obsproject.com/kb/browser-source)).

Use one persistent transparent full-canvas Browser Source. OBS owns placement; the page animates only inside approved slot rectangles. The browser page has minimum page permissions and never receives the OBS WebSocket password. The stream director owns a separate authenticated OBS connection ([obs-websocket](https://github.com/obsproject/obs-websocket)).

[Twitch Enhanced Broadcasting](https://help.twitch.tv/s/article/enhanced-broadcasting) is an ingest/encoding-quality consideration, not an agent/HUD architecture. Treat it as a later output-profile experiment after one stable private OBS encode; it does not change the local overlay, voice or safety boundaries.

Recovery sequence:

1. page loads and authenticates to the local broker;
2. page requests a complete snapshot and last sequence;
3. page applies ordered deltas;
4. disconnect shows a stale indicator while transient effects expire;
5. reconnect discards old deltas, reapplies snapshot and resumes from sequence;
6. stream director verifies visible/scene state separately.

## HUD event families

- `agent.activity`
- `browser.context`
- `form.progress`
- `profile.summary`
- `wallet.summary`
- `market.analysis`
- `trade.intent` and `trade.result`
- `document.image`
- `database.query`
- `vision.annotation`
- `system.health`

An event can choose an allowlisted effect (`enter_scan`, `pulse_busy`, `resolve`, `fault`, `expire`) and bounded duration. It cannot supply executable styling or screen geometry.

## Visual/perception references from the legacy notes

| Source | Reusable idea | Decision |
|---|---|---|
| [Gradio webcam/WebRTC detection guide](https://www.gradio.app/guides/object-detection-from-webcam-with-webrtc) | Fast visual-model prototyping with live webcam frames | Prototype/evaluation UI only; OBS overlay remains project-native |
| [gradio-detection-viewer](https://github.com/hysts/gradio-detection-viewer) | Interactive detector visualization and result inspection | Dataset/QA reference, not runtime compositor |
| [Gradio realtime speech recognition guide](https://www.gradio.app/guides/real-time-speech-recognition) | Streaming UI pattern | Speech implementation stays in Jabberwerk; borrow only demo/measurement ideas |
| [A2UI Theater and renderers](https://a2ui.org/) | Streaming declarative surface/component behavior | Primary HUD protocol reference |

## Browser/computer-use visibility

The overlay should visualize browser/computer-use activity through sanitized events, not connect directly to a browser controller. Examples:

- domain and redacted page title;
- current workflow stage;
- form section and validation result;
- screenshot/region reference after redaction;
- structured result and evidence citation;
- approval/rejection/blocked state.

The browser tool remains isolated and policy-gated. A visual summary cannot replay a command or become an action button.

## Security tests

- unknown protocol/catalog/component/effect;
- prototype-pollution/unsafe JSON Pointer paths;
- excessive tree depth/component count/text/media/update rate;
- remote URL, iframe, script, CSS and event-handler injection;
- phishing-like controls or false approval/status UI;
- stale/duplicate/out-of-order/cancelled events;
- source hide/show, scene switch, page reload and cache refresh;
- broker, renderer, OBS WebSocket and OBS restart;
- GPU acceleration on/off and long-run memory/timer growth.

Success means the HUD fails visually and locally without affecting Hermes, speech, OBS program audio or robot safety.
