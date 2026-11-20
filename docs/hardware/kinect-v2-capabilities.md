---
created: 2026-11-20T11:15:00Z
branch: codex/production-wave-02-task-03
author: Codex
status: active
---
# Kinect v2 capability inventory and visual baseline

This is an **observed implementation inventory**, not live admission or physical
accuracy qualification. The machine-readable [catalog](../../tools/kinect2/effects/inventory.json)
separates sensor measurements, capture transforms, software inference, renderer
presentation and program composition. Each entry carries its input grid, origin,
Mac/Linux implementation state, control surface, evidence and limitations.
`implemented` means code exists; it does not promise that a device is connected,
tracking is successful, an effect is remotely addressable, or a release gate passed.

## Sensor, driver and platform boundary

| Capability | Input and output | Current availability and limits |
| --- | --- | --- |
| Optical RGB | Native 1920×1080 color; published as same-sequence JPEG | **Observed source and private program.** Compression is not raw Bayer data; optical pixels do not provide independent XYZ. |
| IR intensity | Native 512×424 IR delivered to the listener | **Observed source.** Only aggregate `ir_mean` is published; there is no raw-IR image consumer/export in the current ABI. |
| Depth | Native 512×424 grid, at most 217,088 slots | **Observed source and private program.** Invalid/non-finite samples remain absent. Slot count is not valid-point count. |
| Registration | Factory calibration maps color onto the 512×424 depth grid; calibrated XYZ and optical map | **Observed source.** Registered color is resampled RGB. It does not increase depth resolution or independently qualify metric accuracy. |
| Surface basis | Compatible neighboring measured points estimate orientation for shading | **Observed source.** Derived shading normal, not a new hardware channel or filled geometry. |
| Microphone / beamforming | Kinect SDK voice/audio capability is a separate interface | **TBD on this stack.** No microphone subscription, audio device test, channel/rate claim, or beamforming adapter is present. Do not enable a control from sensor marketing alone. |
| Microsoft body / gesture SDK | SDK inference over Kinect sensor data | **Unsupported here.** Microsoft SDK 2.0 documents Windows x64; this Mac/libfreenect2 path does not expose that SDK. |

The pinned [libfreenect2 README](https://github.com/OpenKinect/libfreenect2/blob/fd64c5d9b214df6f6a55b4419357e51083f15d93/README.md)
documents RGB, IR/depth transfer and registration, Mac/Linux/Windows support,
and optional processing backends. The current [producer](../../services/camera-capture/kinect2.cpp)
selects `OpenGLPacketPipeline`, receives Color/IR/Depth, and publishes geometry,
native and registered JPEGs, a registration map and metadata. This is distinct
from upstream optional CPU/OpenCL/CUDA paths or VideoToolbox JPEG support; their
presence in upstream documentation does not qualify the installed build.

The [Microsoft SDK download](https://www.microsoft.com/en-us/download/details.aspx?id=44561)
and [v2 announcement](https://blogs.microsoft.com/blog/2014/10/22/microsoft-releases-kinect-sdk-2-0-new-adapter-kit)
describe Windows v2 software capabilities. They do not establish Mac microphone,
skeletal tracking or gesture support. Kinect v1 and Azure Kinect specifications
are not interchangeable with this sensor. Primary pages were checked 2026-11-20.

## Derived perception and presentation

| Feature | Origin / current control | Evidence boundary |
| --- | --- | --- |
| MediaPipe body and face | Software model inference on registered imagery | Advisory detections, not Microsoft SDK skeletons, identity or calibrated robot pose. |
| Masked ORB robot lock | Template/homography inference | Private template/mask required. Inlier ratio is not a calibrated probability. No match means no object lock. |
| Nearest depth component | Derived geometric region | A surface is not a person or robot identity. |
| Fixed RGB video | Native optical pixels; edge `rgb` / key `1` | Full-frame reference persists through target loss. It supplies no depth parallax. |
| Crimson samples | RGB edge/contrast strokes; edge `crimson` / key `2` | Labelled color samples/depth-probed. Fine contours are optical detail, not extra measured depth. |
| Depth-palette XYZ | Native measured geometry; edge `xyz` / key `3` | Switching preserves camera angle. Missing surfaces remain holes. |
| Crimson XYZ | Measured geometry, local key `4` | Current remote edge has no separate command for this look. |
| Brackets / probe / insets | Derived ROI, measured probe and same-frame real crops | Sequence and TTL must match. Missing optical mapping hides optical graphics; valid XYZ can remain. |
| Stroke width / density | Renderer presentation | Local `[`/`]`: 0.75–3.6 pixels in 0.15 steps. RGB shader occupancy is contrast-derived; no typed density control exists. |
| Orbit / zoom | Virtual camera | Local yaw ±0.55 and pitch ±0.32 radians; distance 0.65–5.0 scene units. Bounded auto orbit stops near ±0.35. No physical camera movement. |
| Existing automatic crop | Color presentation anchored when object ID changes | Crimson crop exists; smoothing, stable reacquisition, saved framing rules and preview/apply/revert remain proposed. |
| Scene / camera blend | Program presentation | No timed, revisioned blend adapter is implemented. Three named edge looks switch discretely. |
| OBS program | Dedicated muted Godot window source | Encoded 1920×1080 at nominal 30 output FPS is separate from sensor delivery FPS. Arbitrary source/scene control is unavailable. |
| Hermes text / timeline | Redacted read-only activity | No tool authority. Desktop screenshots remain rejected; missing screen imagery is offline. |

Implementation authority is [main.gd](../../tools/kinect2/godot/main.gd),
[color_surface.gd](../../tools/kinect2/godot/color_surface.gd), the
[tracker](../../services/camera-capture/detect_targets.py) and
[OBS adapter](../../tools/kinect2/obs-edge.lua). The older
[design note](../../tools/kinect2/godot/DESIGN.md) retains historical font and
screen-port language; current code and qualified operation take precedence.
[Issue 57](https://github.com/patchwerks/furbomek/issues/57) remains the framing
follow-up, not evidence that saved rules already work. Its proposed rule fields
include target selectors and trigger predicates, priority, confidence/freshness
thresholds, dwell/release timing, pan/zoom limits, transition speed and explicit
loss fallback. Manual hold/reset and current target/reason reporting must share
the same persisted policy. None is implied by today's automatic color crop.

## Private baseline, 2026-11-20

**Measured:** one private dedicated-profile recording, 18:05:10–18:05:35 Bangkok,
contains RGB → XYZ → crimson samples → RGB without moving the camera or requesting
robot actions. Typed preflight confirmed OBS idle in test mode; one approved
camera start reached fresh capture and the named Godot source bound. Typed stop
and status confirmed recording off, streaming off, and all camera workers started
for this run stopped. No public or bandwidth-test stream was started.

The 24.433-second H.264 program decoded end to end at 1920×1080, nominal 30/1 FPS.
Its SHA-256 and private artifact locations are retained in execution evidence
`03/baseline.json`; raw media and scene images are outside Git in an owner-only
directory. Extracted windows at 6, 12, 17 and 22 seconds show respectively fixed
RGB, measured XYZ, RGB-derived crimson and returned fixed RGB.

**Observed visual results:** RGB shows the robot and its tabletop scene; XYZ
shows sparse robot surfaces and large missing areas, while crimson outlines
recover optical detail. The two RGB samples retain the same framing. Both right
insets fit inside the full program. No object lock was reported during this run;
XYZ/crimson select a surface region instead. This is not a successful robot
subject-lock demonstration. Small HUD text is soft and low contrast over RGB.
The private reference's crimson visual language is a comparison target, not a
claim of matching human-scene geometry or approved visual fidelity.

| Timing / performance evidence | Result | Interpretation |
| --- | --- | --- |
| Fresh edge capture readings during program | 14.7244–14.7674 paired FPS | Capture's cumulative publication rate, not glass-to-program latency. Startup fresh reading was 13.9882 FPS. |
| Final producer snapshot | 81,841 valid / 217,088 slots; 70,182 colored; 14.79 paired FPS | A single post-program snapshot, not a per-look average or metric calibration. |
| OBS current recording | 734 output frames; 622 drawn / 746 attempted; 124 lagged (16.6%) | Rendering lag reproduced in a short private recording. |
| OBS encoding | 4 / 746 skipped (0.5%) | Encoding skips are separate from rendering lag. |
| Prior public-stream observation, re-read from original log | 903 output; 905 drawn / 1,197 attempted; 292 lagged (24.4%) | Historical run with different duration/output workload; not a matched A/B improvement claim. |

OBS reports **33.0.1 mac**; Godot reports **4.7.2 stable**, OpenGL 4.1 Metal
compatibility rendering. The inventory baseline code revision and actual
producer/renderer file hashes are recorded independently from binary hashes.
A binary hash alone does not prove which source built it. The private 30-fps
encoding does not turn roughly 14.7 new frame sets per second into 30 sensor sets.

**HOLD:** rendering performance is not qualified. These logs localize the reported
misses to rendering versus encoding, but do not isolate CPU, GPU, capture,
compositor, shader or scheduling cost. No per-look GPU/frame-time trace or matched
controlled load experiment was available in the existing typed surface. The run
also overlapped non-live verification, so its load differs from ordinary use.
Do not assign a cause or claim the 24.4% problem fixed. Task 17 still needs its
representative 30-minute performance gate; this short inventory baseline cannot
replace it.

## Validation and remaining gates

`python3 tools/kinect2/effects/validate_inventory.py` validates the catalog using
Pydantic 2; the script pins its dependency for `uv run` use. The deliberately
invalid `--fixture mislabeled-depth` invocation exits 2 and identifies the
RGB-as-depth claim. The validator also rejects native-grid swaps, inferred
measurement claims, excess sample counts, duplicate IDs and missing evidence.
It checks structure/provenance invariants, not the truth of cited reports or
live availability.

Focused tests use the real CLI and model boundary. The camera snapshot fixture
checks missing/reused/partial ring slots. The additional headless Godot
[stream fixture](../../tools/kinect2/effects/tests/stream_fixture.gd) drives the
real loader with stale, mixed and valid synthetic frames, expires a live snapshot,
and recovers only from a new matching snapshot. These are fixture results, not
live tracking-loss qualification.

The required `FURBOMEK_GODOT=… bash tools/verify-media.sh` invocation is recorded
in `03/verify-media.log`. Its initial Mac run passed gateway and activity checks
but failed five supervisor fixtures whose explicit environment mappings omitted
`FURBOMEK_ACTIVITY_SPOOL` and consequently attempted Linux `/dev/shm`. This
inventory change does not alter the supervisor. Independent remaining gates are
recorded separately; a partially passing wrapper is not an overall PASS.

Still unqualified: metric depth accuracy, near-range behavior on controlled
targets, dark/reflective-surface error, mic/audio capabilities, live-human
recognition, continuous robot lock, safe stage observation, saved framing rules,
performance soak and unattended operation. The 0.25–8 m software depth filter is
not a measured usable range. No hardware, firmware, robot controller or OBS credentials were changed.
No settings were manually edited. The existing OBS adapter performed its normal
dedicated-window binding during typed status checks.
