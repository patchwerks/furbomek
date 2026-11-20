# Furb-o-Mek movement schematics

These plates show what the installed controller commands, from the starting
stance through each change in foot target. The geometry is schematic. The
notes beside each plate give the exact programmed offsets and describe what
can be seen in the recorded test.

Each movement page pairs an ImageGen illustration with an exact target
map. Use the target map or phase data to check small shifts and starting
markers that can be simplified in the illustrated plate.

| Movement | Figures | What is implemented |
| --- | --- | --- |
| [Poke](poke.md) | 1–5 | Lift one leg, reach, hold, retract while lifted, plant. |
| [Defensive brace](defensive-brace.md) | 1–15 | Lower, widen by tripod, hold, restore width, rise. |
| [Tuck preview and curl-up intent](tuck.md) | 1–15 | Lower, narrow by tripod, hold, restore width, rise. The commanded end pose is standing. |
| [Heighten and Sleep](heighten-sleep.md) | 1–6 | Raise into normal stance or lower into the existing Sleep stance. |
| [Forward and scuttle baseline](forward-scuttle.md) | 1–5 | One Forward request runs both alternating tripod phases. |
| [Backward / recoil](reverse-strafe.md#backward--recoil) | 1–3 | One reverse tripod phase. |
| [Strafe left](reverse-strafe.md#strafe-left) | 4–6 | One leftward tripod phase. |
| [Strafe right](reverse-strafe.md#strafe-right) | 7–9 | One rightward tripod phase. |
| [Turn left and turn right](turns.md) | 1–6 | One tripod phase on the requested turn arc. |

## Reading the plates

- Top views hold the chassis fixed, with the head end at the top. Colored
  endpoints are foot targets in the body frame. Teal is tripod A, legs 1, 3,
  and 5. Amber is tripod B, legs 2, 4, and 6. A hollow colored ring is a lifted
  target. A solid colored dot is a target at the current stance height.
  Small gray rings mark starting targets where they differ.
- In foot coordinates, positive Z is upward. Positive Y is forward. Positive
  X points left on these top-view plates, following the firmware convention.
  A body lowering appears as an upward foot offset in the body frame.
- **Commanded millimeters** describe offsets computed by the firmware.
  **Measured pixels** are from a particular camera view and describe image
  motion. Joint angle measurements on this unit are unavailable. The plates
  use the commanded Cartesian paths and supported observations as their scale
  of evidence. Their geometry is a visualization rather than a fabrication
  template or confirmation of foot contact.
- [Phase data](phase-data.json) provides numerical target coordinates in
  the order shown. The [generation prompts](prompts.md) document the
  ImageGen work.

## Evidence

The most recent verified Mega application for this set is the larger-gesture
image, HEX SHA-256
`07f2e7149bf6945c4b9b9015a70e536a6639e28ea768d6eb2a44dd7f13a06ca3`.
The exact Poke, Brace, and Tuck commands come from
`firmware/freenove-guard/src/expressive_motion.cpp` in the expressive motion
worktree, cross-checked against the emitted nominal trajectory and the
installed-image record.

The 2026-11-21 Kinect pass shows the larger gestures on the center support.
Its installation and measurements are recorded in the macOS worktree at
`docs/operations/macos-expressive-gesture-tempo-2026-11-21.md`. The
front-view supported clip SHA-256 is
`5cee83c6af0e3acaed3f4bbf3c3cc929d8ec47080530b39186647bd37ded8822`.
The larger gestures were measured on the support. The bare-table record
for the earlier smaller gestures describes the earlier firmware.

The legacy gait and vertical-stance illustrations use the local pinned
[Freenove source archive](../../docs/hardware/vendor/freenove/INDEX.md)
and the Mac gateway's per-action phase counts. Their physical observations
were recorded on 2026-11-20 in the macOS worktree at
`docs/operations/macos-persistent-bridge-tabletop-2026-11-20.md`.
The private tabletop recording SHA-256 is
`b247947c71306b17b1502504ba3d7d8046a7fce777e49b46ce636de81b8522c7`.
Original recordings stay in private evidence storage.
