# Research brief

Core question: Which three to five Linux-native FOSS visual-production stacks best reproduce the supplied red point-cloud/tracking/HUD/glitch video for Furb-o-Mek, using the owned Logitech C922x now and a low-cost Kinect v2 depth path later?

Codebase relevant: yes. External sources: yes. Rendered browsing: yes. Verification: yes. Scale: 15 distinct research lanes plus refinement; cost of a wrong recommendation includes hardware spend and an unusable live pipeline.

Axes: current Furb-o-Mek architecture; target perception/HUD/OBS boundaries; frame-level effect inventory; openFrameworks; Godot; Praxis LIVE; Processing; OBS/GStreamer/OpenCV; Kinect v2 driver; depth-camera counterfactuals; C922x Linux capture; tracking and point-cloud algorithms; streaming/agent control; rendered vendor/project pages; skeptical compatibility/licensing review.

Expected truths: a selected stack must be Linux-compatible and FOSS; accept live C922x RGB; accept Kinect v2 RGB/depth/IR via a maintainable bridge; express every visible effect; feed OBS or replace it credibly; admit bounded programmatic control; and fit the repo's staged architecture. A camera price, equivalent performance, or exact effect match is not assumed before evidence.

## Deliverable

- lane: no-format (answered_by: request)
- state: none (answered_by: observed outcome state)
- formats: markdown (answered_by: request)
- destination: `docs/research/linux-live-visuals-touchdesigner-alternatives-2026-10-01.md` (answered_by: request)
- audience: Furb-o-Mek engineering decision, deep (answered_by: request)
- template: existing `docs/research` evidence-note conventions (answered_by: destination)
- format description: cited research overview with ranked 3-5 best fits, exact video-effect matrix, camera constraints, integration/acceptance gates (answered_by: request)
