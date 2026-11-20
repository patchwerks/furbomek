# Tabletop motion observations without tags

On 2026-11-20, Furb-o-Mek ran seven bounded actions on a bare tabletop with
the operator at the physical POWER switch. The MacBook controlled the
untethered chassis through the handheld USB/RF bridge. The Logitech C930e
recorded privately at 640 × 480 and 15 fps under a flashlight. The fixed
view was suitable for scoring chassis movement. Some feet were obscured.

Powered idle reported 8.20 V and fault 0. ARM-only showed no observable
chassis movement and verified DISARM. Every dispatched action reported
completion and verified normal DISARM. The bridge closed after the last
action. The operator later reported leaving physical POWER ON. A read-only
request to the Mac gateway returned `local_bench_closed`.

| Action | Phases | Observed result |
| --- | ---: | --- |
| Active | 1 | Legs extended. The chassis image moved about 7 px up as it rose. |
| Forward | 2 | Settled about 27 px right and 1 px down, toward the head side of the frame. |
| Backward | 1 | Settled about 12 px left and 2 px up, opposite forward. |
| Left | 1 | Settled about 11 px up, with about 2° of counterclockwise rotation. |
| Right | 1 | Settled about 10 px down, with under 1° of rotation. |
| Turn left | 1 | Settled about 3° counterclockwise. |
| Turn right | 1 | About 3° clockwise in the last frame. Capture ended before a settled pose could be verified. |
| Sleep | — | The bridge window expired before dispatch. It included the wait for power-on. |

The first score used snapshots triggered by guard completion. Several
snapshots still showed movement. The table above uses the median of twelve
settled video frames where available. Chassis tracking subtracts background
motion and cross-checks two other regions of the robot. The projected offsets
describe this view without using the table dimensions. The
[expressive motion catalog](../hardware/expressive-motion-v1.json) records
the exact frame intervals, evidence for each named movement, and what to
measure for a new pose or sequence.

The guard executed more than one bounded action in a single ownership
window. The previous gateway released the serial port when that window
ended. The [bridge follow-up](macos-brodex-edge-2026-11-20.md#persistent-bridge-follow-up)
separates USB ownership from motion admission. Unattended startup, stage
clearance and reconnect behavior still require physical qualification.
The trial had one sample per action and provides no metric distance,
repeatability, full-foot tracking, or unattended qualification. The local
Mac gateway ran the commands. This trial did not verify the Brodex MCP route.

The private recording, guard trace and initial snapshot scores are stored
together as `table-pass.mkv`, `guard.jsonl` and `motion-map.json`. The recording
decoded end to end. SHA-256 evidence follows.

| Artifact | SHA-256 |
| --- | --- |
| Recording | `bd4e1d47d48679966fea672b8066505c9ea43eb8d3123fa1fce80c680754c2b9` |
| Guard trace | `d3a9ff65f9ad02fffb9b5cbc9b95331dcc07df96dff041fe0cfd4772b67f25c1` |
| Local gateway `guard_action.py` | `48b4a5aefca4611559f7c8a2b2bd2c1343688f38c0e0d95823a40ccc41a813d2` |

The test used the deployed guard and changed no device images or
configuration. There was no candidate image, flash, reset, or new firmware
readback. The prior installed hashes in
[the firmware record](../hardware/firmware.json) still describe the last
verified images.
