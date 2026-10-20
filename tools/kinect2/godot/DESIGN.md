# Furb-o-Mek Kinect 2 Broadcast Design System

## 0. Reference Extraction

- **Observed reference:** `upright-1.8.png` and `upright-4.4.png` are 1920 x 884 crimson sensor compositions. Their source video is sideways; these upright images are the visual authority.
- **Constraint:** The current camera sees the Furb-o-Mek bench scene rather than the reference person. The renderer must match the reference's visual language and data-linked behavior, not claim pixel-identical human imagery.
- **Composition:** near-black stage; a dense central sensor reconstruction; upper-left sensor readout; a narrow left activity/context stack; and two linked chamfered insets at upper-right. Keep the main subject unobscured. Phone-pill and recording-frame artifacts in the reference are excluded.

## 1. Tokens

| Role | Token | Value |
|---|---|---|
| Stage | `stage_black` | `#050204` |
| Oxblood shadow | `shadow_oxblood` | `#26070C` |
| Scan base | `scan_crimson` | `#A5232E` |
| Scan hot | `scan_hot` | `#EC3E49` |
| Tracker | `tracker_pink` | `#F15A8C` |
| Text | `ink_dusty` | `#C69A9A` |
| Muted | `ink_muted` | `#895158` |
| Probe | `probe_amber` | `#FF9B42` |
| Offline | `offline_red` | `#7E2630` |

## 2. Type, Scale, and Surface

Use DejaVu Sans Mono or Liberation Mono in uppercase. The title is 19 px, track labels 15 px, camera panel headers 12 px, port headers/telemetry 10 px, NOW title 12 px, activity primary rows 11 px, activity details 10 px, and fine probe metadata 9 px at the native 1920 x 1080 canvas. Text is dusty pink, never white. Legacy public preview images use RGB multiplier `(0.45, 0.30, 0.33)` so a white page cannot dominate the sensor subject. The Hermes desktop screen uses the lighter `(0.90, 0.63, 0.68)` multiplier: it belongs to the crimson field while preserving a readable browser title or app surface.

Panels are thin 2 px crimson chamfered outlines over translucent oxblood-black, with 30 px header strips and a 5 px hot status bar. Alignment ticks are 2 px and sparse. There are no rounded SaaS cards, gradients, fake metrics, or decorative full-box trackers.

## 3. Point Surface

Contour hierarchy is mandatory: local RGB gradients/contrast drive stroke occupancy, flat bright walls are sparse, and dark material inside the actually tracked object ROI has lifted contour/detail response. Do not render every screen cell with a nonzero red floor. The magnifier uses its own edge/local-contrast response at panel scale so it reveals real source structure rather than uniform stochastic grain. The robot ROI is derived from an annotated private object mask transformed by its observed template homography, never an arbitrary HUD shrink.

Keep the environment subordinate but continuously readable with very dark source-luminance underpainting beneath sparse contours, not a uniform stochastic carpet. Calibrated mask-map outliers are robustly trimmed upstream before publishing object bounds. Magnification is a truly local calibrated-probe crop, sized from the smaller optical ROI dimension; no mapped probe means no processed color magnifier. The amber marker stays hot while its long leader is a subdued one-pixel link.

Default presentation is a high-resolution RGB-sampled fine-stroke field from the same native optical frame as the depth/tracker snapshot, labelled `COLOR SAMPLES / DEPTH-PROBED`. This preserves optical detail that the 512×424 depth sensor cannot measure on dark robot parts. It is a visual sampled surface, not extra measured XYZ. Native measured geometry remains available with `3` (depth palette), `4` (crimson XYZ), arrows and orbit controls. The measured probe uses its actual registered optical coordinate in color-sampled mode; brackets use the corresponding real optical ROI. Do not claim the color field supplies depth parallax or metric detail. Both modes expire with the same source snapshot.

Fine-detail correction: crimson splats remain individually staggered, approximately 1.5–2.2 screen pixels wide with pixel-height short strokes. They must not merge into continuous horizontal raster bands. Use a dark-to-crimson ramp with a geometry-readable floor so black robot parts remain visible, without additive emission blowing walls into solid red. The processed magnifier shows sampled strokes rather than a smooth red-tinted photograph. Evidence includes the entire native 1920×1080 client, never a desktop-clipped 1920×1011 crop.

The cloud is the primary image: 512 x 424 native points rendered from all 217,088 slots by GPU MultiMesh. Default crimson uses luminance ramps and alpha-driven contour gaps. A screen-space quad becomes a 1-2 px horizontal rounded short stroke, never a world-space tile. Invalid depth remains absent and no holes are fabricated. RGB and depth are explicit diagnostic modes, not alternate art directions.

## 4. Data-Led Overlays

Only tracker snapshots whose JSON sequence, cloud header, registered JPEG prefix, and optical JPEG prefix agree may render. A selected detection prefers face, then object, then body; it retains its stable ID while available without a lower-priority fallback monopolizing selection. Up to 64 actual measured ROI samples are projected by the current Camera3D for tight magenta corner brackets, with a world-box fallback. The actual `probe_world` projects to an amber probe and leader to the processed inset. A surface is never made the primary giant box when object/body exists.

The upper right `01 / TARGET MAGNIFICATION` uses the same-frame native optical image in color-sampled mode, magnifying the calibrated probe's neighbourhood with edge/local-contrast strokes; measured-XYZ mode uses the registered image and source ROI. The lower `02 / OPTICAL HEAD WINDOW` crops the matching native optical image, preferring face; otherwise it is labelled `OPTICAL TARGET`. Missing calibrated optical mappings are absent, never whole-frame substitutes: hide color-mode brackets, probe and crops while retaining valid XYZ tracks. These are actual source crops, not invented depth imagery.

## 5. Reusable Primitives and States

- **Chamfer panel:** dark header, cut upper-right corner, 2 px crimson edge, image or text payload.
- **Corner tracker:** four open L arms only; selected current track / hidden when expired.
- **Surface probe:** amber corner marker, actual projected sample, leader to inset / hidden when unavailable or expired.
- **Hermes screen port:** a 440 px-wide chamfer panel at roughly `x=36..476`, below the global header, with a 420 x 236 16:9 inset, a thin crimson edge, tracked header/status strip, and no retained frame for shuttered, offline, stale, missing, or invalid activity. The screen visual state is `LIVE`, `SCREEN STALE`, `PRIVACY SHUTTER`, or `SCREEN OFFLINE`.
- **Now port:** directly below the screen port; presents the public status chip, tool, title, and one cleanly truncated detail line in mono. `ACTING` is hot crimson; `THINKING` and `AWAITING APPROVAL` amber; `PRIVACY SHUTTER` and `ERROR` muted red; `IDLE` muted. It never flashes solely for decoration.
- **Activity timeline:** a fixed lower-left port with at most six read-only rows: compact age, category, action, then dimmed detail. `running` rows are hot and `error` rows muted red. A missing/invalid activity event leaves it empty.
- **Activity port compatibility:** v1 remains a read-only public activity / `IDLE` / `AWAITING PUBLIC ACTIVITY` projection; optional v2 screen/timeline fields do not create invented work. Its legacy safe PNG preview remains supported when a v1 producer supplies it.
- **Context port:** camera-derived sequence, source FPS, valid point count, and feed state.

## 6. Interaction and Accessibility

`1` RGB, `2` crimson, `3` depth; `[` and `]` bound pixel stroke width; arrows orbit; wheel zoom; `O` toggles bounded auto orbit; `R` returns to a head-on stage view; `Esc` exits. Text states distinguish LIVE from OFFLINE without relying on color. The fixed 1920 x 1080 canvas is capture-first accepted debt; it scales as canvas items for smaller display surfaces. The Hermes left column intentionally occupies only the far-left `x=36..476` region and begins below `y=94`, protecting the title header, central robot, and right-side insets. When the sensor is offline, its central annunciator begins at `x=520`, never behind the Hermes activity stack.

## 7. Freshness and Design Debt

The source uses `produced_unix_ms` plus `ttl_ms` solely to determine freshness. Receipt/monotonic times are not presented as glass latency. When the source is stale, cloud, brackets, probe, and insets disappear and the stage states `OFFLINE`; a convincing frozen frame is prohibited. The current real bench scene intentionally cannot visually pixel-match the reference's human scene.
