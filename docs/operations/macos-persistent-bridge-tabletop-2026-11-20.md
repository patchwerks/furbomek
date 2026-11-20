# Live tabletop pass on the persistent Mac bridge

On 2026-11-20 the operator confirmed physical POWER OFF, an untethered robot
on the bare tabletop and presence at the POWER switch. The installed Mac
gateway opened the handheld once and reported `prepared_waiting_for_robot`.
The operator switched POWER on and confirmed stillness and hands clear.
The local ARM-only preflight verified DISARM at a reported 8.15 V.

The Mac edge sent all eight supported actions in one supervised motion window.
Each returned `completed_and_disarmed`. Forward executed the deployed
two-phase gait. The fixed Logitech webcam recorded the chassis throughout
the pass at 640 × 480 and 15 fps under the flashlight.

| Action | Gateway round trip | Settled movement in camera view |
| --- | ---: | --- |
| Active | 1.10 s | Chassis rose about 8 px. |
| Forward | 1.82 s | About 30 px toward the head side of the frame. |
| Backward | 0.90 s | About 16 px in reverse. |
| Left | 1.10 s | About 12 px of lateral travel. |
| Right | 0.91 s | About 10 px of lateral travel. |
| Turn left | 0.99 s | About 3° counterclockwise. |
| Turn right | 1.00 s | About 3–4° clockwise. |
| Sleep | 1.10 s | Chassis moved about 7 px down, with minor foot repositioning. The visible stance was still wider than the initial compact pose. |

Chassis feature tracks in three regions were corrected against the static
scene. Measurements compare a frame immediately before the request with a
frame captured after a 2.2-second settle wait. The image-plane values have no
metric scale and are independent of table dimensions.

After window expiry, the same bridge returned `read_only_bench`. RF
status reported DISARMED, idle, fault 0 and no reset required. Supply still
reported 8.15 V. The Mac retained USB, and the operator could step away
without toggling power. No new firmware, reset, terminal STOP or broadcast
was used. This was local Mac edge dispatch in a supervised tabletop pass.
Poke, a defensive brace and a full curl need further pose work. Unattended
stage motion requires separate qualification.

| Private evidence | SHA-256 |
| --- | --- |
| `table-bridge.mkv` | `b247947c71306b17b1502504ba3d7d8046a7fce777e49b46ce636de81b8522c7` |
| `guard.jsonl` | `8d331a474180d4cb68979344e9d161d7b50aafcf535e46fb9bf21768fa3ef977` |

See the [expressive motion catalog](../hardware/expressive-motion-v1.json)
and the [installed firmware record](../hardware/firmware.json).
