# Sheet 06 — Eye/camera integration

Companion drawing: [06-eye-camera-integration.svg](./06-eye-camera-integration.svg)

## Decision summary

The current external OBS camera is the Phase 1 vision source. It is already the lowest-risk path to perception, overlays, recording, and streaming. No camera has been proven to fit an eye or forehead cavity in the installed head.

A later **single fixed camera behind a reversible forehead or eye insert** is the preferred embedded experiment. Dual/stereo cameras or a moving-camera eye are not justified until one fixed path passes mechanical, optical, thermal, bandwidth, and balance tests.

The user’s 1–3 mile goal is preserved as a later system-level objective. It is not a property of an eye camera and cannot be promised from module specifications alone.

## Comparison

| Option | Evidence/status | Benefits | Risks / gate |
|---|---|---|---|
| Existing external OBS camera [201] | Current/observed system input | No destructive head work; easiest calibration, cooling, service, and stream integration | View is not first-person; robot can leave frame |
| Reversible forehead insert [211] | Proposed | Fixed monocular view; less interference with eye linkage than replacing a moving eye | Must measure depth, shell curvature, ribbon route, heat, balance, and focus |
| Reversible eye insert [212] | Proposed; fit unproven | Strong character POV | Aperture/eyelid/eye-bar occlusion, motion blur, cable fatigue, cosmetic loss |
| Dual eye/stereo [213] | Deferred research | Potential depth cues | Alignment, bandwidth, heat, space, synchronization, calibration, added mass |
| 1–3 mile link [221] | Goal; site/regulatory feasibility TBD | Remote telemetry/video envelope | LOS/Fresnel, antenna height, terrain, weather, spectrum/DFS, interference, latency, jurisdiction |

Raspberry Pi lists Camera Module 3 at **25 × 24 × 11.5 mm** and a starting price of $25 ([official page](https://www.raspberrypi.com/products/camera-module-3/)). Those dimensions show why only the lens can plausibly align with a small eye opening; they do not demonstrate fit. Other camera/SBC choices remain candidates only after exact interfaces, encoding, power, heat, and availability are compared.

## Reversible fixture gate

Before cutting or gluing:

1. identify head generation and document the full mechanism through one hand-turned cycle with power removed;
2. measure eye opening, lens-to-shell distance, internal width/height/depth, eyelid and eye-bar sweep, cam/gear clearance, and cable exit radius;
3. use a removable dummy volume and lens target to test field of view, focus, vignetting, reflections, fur occlusion, and appearance;
4. fixture the camera without modifying original linkage; demonstrate full-cycle clearance and strain relief;
5. record temperature, power, mass/balance, vibration, motion blur, encoder latency, and dropped frames;
6. preserve a reversible external-camera fallback.

An embedded camera must not share a power path in a way that lets video brownouts corrupt the motion watchdog.

## Video and control architecture

Locally, an onboard encoder/SBC may send H.264 over a private IP link to the offboard media host. Use timestamped frames and bounded buffers; stale frames must be dropped rather than accumulating control-delaying latency. [RFC 6184](https://www.rfc-editor.org/rfc/rfc6184) defines H.264 RTP payloading, while [RFC 8834](https://www.rfc-editor.org/rfc/rfc8834) describes WebRTC media requirements.

Control and video are logically independent:

- the robot-mounted gateway stops from control-heartbeat/TTL loss;
- video loss never keeps motion alive and never substitutes for the control watchdog;
- the offboard director may request a safe state when video quality crosses policy thresholds, but local expiry remains authoritative.

## 1–3 mile feasibility gate

Before selecting a long-range radio, document the operating jurisdiction, frequency/bandwidth/EIRP constraints, DFS or coordination requirements, endpoint and antenna heights, terrain/obstructions, Fresnel clearance, expected throughput, interference, weather exposure, encryption, and safe recovery area. The FCC U-NII rules are one relevant US reference, not a universal permission ([47 CFR Part 15 Subpart E](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-E)).

Test in staged distances at the actual site and record packet loss, jitter, video bitrate/quality, glass-to-glass latency, control round-trip, reconnect time, and stop distance after forced loss. Beyond-visual-line-of-sight or public-space operation may trigger additional local rules; obtain jurisdiction-specific review.

## Acceptance evidence

- Dimensioned cavity/sweep model and reversible fixture photographs.
- Optical target captures across lighting and mechanism positions.
- Thermal/power/balance and encoder-latency logs.
- RF site survey, link budget, regulatory basis, and staged loss/recovery test.

## Stop conditions

Do not cut the shell, remove a functioning eye linkage, buy paired cameras, or claim 1–3 mile capability until the applicable measurement and site gates are passed.
