# ULW research synthesis: Linux live visual effects for Furb-o-Mek

Research team: 15 distinct opening axes, two expansion waves, 0 off-axis excursions. Refinement team: 5 independent perspectives. Sources ledger: 115 cited source entries across 27 domains at final reconciliation. Executed checks: video ffprobe/frame render, price Decimal arithmetic, Markdown/local-link scan, Mermaid CLI render/XML parse/pixel inspection. No Linux camera, Kinect, renderer or OBS hardware trial.

## Executive summary

Godot 4 with a separate camera/perception process and OBS best fits the planned reusable Furb-o-Mek renderer, while cables.gl standalone is the closest current Linux FOSS visual-node authoring experience. openFrameworks is strongest for direct depth/C++ control; Praxis LIVE is a capable live visual patcher; OBS + shaderfilter/OpenCV is the fastest RGB broadcasting proof. None has an observed complete implementation of the supplied MOV or a verified native .toe/.tox importer. [S18][S32][S16][S12][S21][S35]

The existing C922x can feed the clip's sampled-red RGB visual, tracked boxes, insets, probe and HUD through software. The clip does not prove measured depth. Kinect v2 supplies genuine RGB/IR/depth and registered XYZ through libfreenect2, subject to USB3/power/controller and host qualification. A live apparently complete used kit was listed at displayed $39.32 pre-tax, correcting a $150-only early price impression. No investigated alternative matched that acquisition price without a specification/host/modality tradeoff. [S4][S8][S10][S11][S41][S27][S28][S29]

## Findings by theme

### Reference video

Observed red sampled person/room surface, moving body frame, early face lock, later gold probe, processed magnifier and photographic head crop. No source software, camera identity, metric depth, FPS or latency is observable. See V1 in the final report and wave-1-video-effect-forensics.md. Claim nodes C01-C02.

### Software

Godot CameraServer/MultiMesh/SubViewport and WebSocket support a programmatic scene, with external depth/tracker bridge. cables AppImage/node editor has webcam/pose/face/render nodes but native-privilege authoring, CDN-dependent models and HTML native-op mismatch. OF Linux capture/shaders/points are strong but its v2 addon targets an older core. Praxis Linux V4L2/GLSL is direct, metric depth custom. OBS directly owns camera/stream/HUD sources but requires external recognition/3D renderer. Evidence is source/API capability, not runtime throughput. Claim nodes C11-C15. [S18][S19][S20][S32][S33][S36][S37][S16][S17][S12][S13][S21][S22][S23]

### Cameras and prices

C922 vendor publishes RGB modes and UVC1.1; actual Ubuntu device modes untested. Kinect v2 driver publishes 1080p color and 512x424 IR/depth with registration; Ubuntu24.04 route is supported by a third-party tested integration and a Noble PPA package. Live Mercari offer and seller photos support an apparently complete $39.32 pre-tax bundle, with condition/USB3/actual depth unverified. RealSense direct stores displayed $325/$375 base plus surcharge, not old comparison-page $272/$314. Claim nodes C03,C05-C09. [S8][S9][S10][S11][S38][S39][S41][S25][S26]

### Repository

Checked-in app is audio/chat/TTS with video disabled. PLAN.md places external OBS camera first, planned broker/HUD/perception and independent OBS director later; renderers receive bounded state, not Hermes or robot authority. Claim nodes C04,C17. [S1][S5][S6][S7]

## Codebase findings

- ../../app.vue:200-240 calls getUserMedia with video disabled; :207-208 filters audio devices.
- ../../src/chat/openai-assistant.ts:47-59 takes text messages.
- ../../PLAN.md:424-500 sets OBS/A2UI/perception boundaries; :606-620 gives runtime budgets; :845-870 gives tracer-bullet phase.
- ../../docs/research/runtime-ui-stack-2026-09-21.md records previous broker/HUD/renderer decisions.

## Sources ranked

1. User MOV SHA256 in final report V1, direct evidence for exact visible composition.
2. Project PLAN.md and checked-in app, direct evidence for current/planned distinction.
3. OpenKinect pinned driver README, frame and registration code [S10][S11], primary depth capability.
4. Logitech first-party specs and OBS guide [S8][S9], camera published capability.
5. Godot, cables, OF, Praxis and OBS first-party docs/source [S18][S19][S32][S16][S12][S21], candidate primitives.
6. Browser-rendered live Mercari listing [S41], precise time-bound price and photo, single-seller exception.
7. Direct RealSense/Orbbec/Arducam/Luxonis stores [S25-S30], volatile price/spec evidence.
8. Derivative TouchEngine/file-type docs [S35], portability limit.

## Verified claims and epistemic instrumentation

The verified-claims digest and full dependencies/counter-search are in claim-graph.md. intent-diff.md closes I1,I3-I6 as source-supported or qualified and leaves I2 exact deployment parity unknown until a candidate recording exists. observation-manifest.md records provenance, temporal validity, observer groups and contamination. verification-economics.md identifies which cheap checks ran and why hardware claims remain unverified. cause-disappearance.md records corrected price and Ubuntu inferences.

## Contradictions resolved

- Early complete Kinect example $150 versus later live $39.32 apparent bundle: later search establishes a cheaper individual offer, not a durable market floor. [S24][S41]
- Stale RealSense comparison page versus direct store: use $325/$375 base and note surcharge/stock. [S25][S26]
- Old libfreenect2 Ubuntu issue versus later Noble package/instructions: Ubuntu24.04 feasible by source evidence, actual host not tested. [S10][S38][S39]
- Mosaic 'Kinect' node versus v2 requirement: source includes ofxKinect v1, so no v2 native node claim. [S40]
- cables 'offline' editor versus CDN model files: offline rendering of tracking requires repackaging and a cold run. [S37]
- .tox embedding versus Linux FOSS project import: TouchEngine is an external licensed Windows/macOS path, not a verified importer. [S35]

## Gaps and unresolved

No exact-host C922 mode inventory, Kinect sensor/USB/controller test, actual OBS/Godot/cables/pipeline FPS/latency benchmark, candidate exact-look recording, model-weight/license inventory, or native TouchDesigner graph converter. These are stated as acceptance gates in final report, not silently treated as source facts. C09 is partial rather than universal: the zero-tradeoff negative finding is limited to investigated offers and can change.

## Expansion trace

Wave 1: 15 axes produced candidate/source/price/driver/video facts. Wave 2: cables, Ubuntu Kinect, Mosaic and visual acceptance resolved shortlist omissions and compatibility claims. Wave 3: cables HTML/offline export and sub-$100 complete used kits settled two answer-changing leads. Remaining leads require deployment hardware, an implementation, or a fresh price read at procurement, so the source-only graph converged. Refinement team corrected exact-look overclaim, OBS crash fallback wording, camera price caveats and citations.
