---
created: 2026-11-19T20:00:00Z
branch: codex/macos-bring-up
author: Codex
status: active
---
# One bare-table forward trial

On 2026-11-20 the operator confirmed physical POWER OFF, charger isolation,
clearance on the table and presence at the physical cutoff. The robot was
placed on its feet with its center support removed. The body USB cable was
unplugged before the action. The handheld stayed connected over USB and
communicated with the robot by RF.

An exclusive, local Mac test process reused the installed Guard transport
and admitted one `forward` command. The off-state gate read DISARMED and
reported 0.06 V. The operator observed stillness on power-up. ARM-only
verified DISARM at a reported 8.19 V. The one forward command completed
and verified DISARM at 8.19 V. Final telemetry was DISARMED, idle and
fault 0. The test process released the port. The operator subsequently
confirmed physical POWER OFF.

The optics show a leg and chassis posture change. The evidence does not
establish clear forward translation across the tabletop. The OBS program
reframed to a fallback detection during the recorded interval, and the
reference images do not provide a calibrated travel measurement. No
second action, emergency STOP, firmware readback, writes or controller
reset was commanded. The [installed records](../hardware/firmware.json)
retain the verified image identities. This single supervised trial does
not qualify autonomous motion.

The private OBS recording SHA-256 is
`19b0b42b2df8fa747a01d203f5910897eac33e0d83ac2c6336e60fc5233761d9`.
The private Guard log SHA-256 is
`5894c935c4da9d762ea52d8e167c30eb61f66181811e505d9984d1cc23425b97`.
The public broadcast remained idle.

## Framing follow-up

The renderer previously auto-cropped to a selected fallback body or
surface after losing the robot. The main color view now presents the full
frame while there is no valid robot target. The updated preview was
observed in idle OBS with the tabletop robot visible. The secondary
optical inset still had a fallback target in that view. A table-view
template trial did not reacquire the robot, and the prior private assets
were restored.

[Issue #57](https://github.com/patchwerks/furbomek/issues/57) tracks
configurable framing and pan rules for the streaming pipeline.

The [two-phase tabletop follow-up](macos-table-walk-and-media-2026-11-20.md)
records the short forward advance and the fixed optical view.
