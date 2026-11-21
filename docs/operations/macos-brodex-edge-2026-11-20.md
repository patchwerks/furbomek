---
created: 2026-11-19T19:13:00Z
branch: codex/macos-bring-up
author: Codex
status: active
---
# Brodex control of the macOS device host

The Mac runs the user LaunchAgent `dev.patchwerks.furbomek-edge` during its
desktop session. It authenticates to Brodex through the existing SSH alias
and reverse-forwards one Unix socket. The Brodex relay verifies the
forwarded socket's owner and mode, then publishes an owner-only
`~/.local/state/furbomek-edge/current/control.sock` route. The agent rebuilds
that route on reconnect. It starts with the camera stopped and the bench
closed. Neither the relay nor the OBS adapter requires a new TCP listener.

Chezmoi owns the MCP entry in the Brodex `furbomek` profile. Its stdio client
offers the existing robot state, supply, capabilities, action and STOP
tools, plus `kinect_control` and `obs_control`. The edge runtime is installed
under the profile owner's private Furbomek state directory. A discarded
or expired request produces no automatic action retry. The installed
gateway's reconciliation compares server names. During migration, the
operator briefly disabled only the parked legacy `furbomek` registration,
reconciled that profile, then restored the Mac template and reconciled it
again. The shared Hermes gateway stayed up.

## Robot admission

Only the Mac agent's separate local operator socket can prepare the bridge,
enable a supervised motion window, or close the bridge. An initial
`prepare` opens USB after fresh physical POWER-OFF confirmation. A healthy
idle reply with off-state voltage admits telemetry. If both status and supply
time out, the Mac can hold the already-open USB bridge read-only until the
robot comes online. A timeout provides no power-state evidence. The robot's
removable cells charge in a separate box.

The operator verifies support, clearance and stillness before the first powered
pass. Local `enable` checks voltage and runs ARM-only with verified DISARM.
The Mac uses the same open bridge for subsequent windows, including after
idle expiry or an idle Brodex disconnect. The operator can leave power on
between passes in that held session. A fresh local enable is required after
expiry or disconnect. Local close and daemon shutdown release the USB
connection. Removing or replacing the bridge requires a new preparation.

Each window lasts up to two minutes. Each action must have at least eight
seconds left in the window to accommodate its entire transaction. The
Mac admits one request at a time and refuses competing commands without
queuing. Each action starts from fresh DISARMED, with local voltage, phase,
deadline and firmware watchdog checks. A BOOT reply revokes motion and
requires a new ARM-only preflight through the held bridge. STOP bypasses the
request gate. Deadline and tunnel loss cancel in-flight motion. Normal
completion verifies DISARM, while interrupted operations use the existing
terminal STOP path and preserve firmware fault latching.

The tabletop candidate defines named `table_hold_low`,
`table_hold_middle`, `table_hold_high` and matching
`table_walk_low`, `table_walk_middle`, `table_walk_high` actions.
The `_fast` variants select 3.75 mm per trajectory update. Each name
is subject to the same local explicit action allowlist. The five-second
holds use a six-second host poll budget inside the existing eight-second
edge request budget. Only enroll choices verified on the actual table.

The bench operator verified all twelve tabletop presets under load,
with both cameras and a verified DISARM after each command. See the
[tabletop results](https://github.com/patchwerks/furbomek/commit/99c0ed7).
The Mac edge now loads the twelve names and Active as the local
allowlist for the installed tabletop application. The earlier
allowlist was backed up with the private configuration. The Brodex
`furbomek` stdio client loaded the same twelve names. A fresh Hermes
MCP connection discovered all seven tools, and a read-only query
through the registered MCP command reached the Mac with the local
motion bench closed. Loaded motion was observed through the
isolated bench session. The Hermes check exercised schema and
transport with the bridge closed.

At handoff the owner confirmed physical POWER OFF and the body USB
unplugged. The private test session released the handheld. Mac
operator preparation returned `prepared_waiting_for_robot`, and the
Mac edge process took exclusive ownership of the handheld. A live
`robot_get_capabilities` query through the enrolled Brodex profile
returned `read_only_bench`, with exactly Active and all twelve
tabletop presets in the allowlist. Powered admission was false.

### Powered Hermes tabletop verification, 2026-11-21

The operator confirmed the bare tabletop, body USB absent, stillness
at POWER ON and presence at the physical switch. The Mac continued
to hold the handheld. A stale reverse SSH session was reconnected
through the dedicated child process. The running Hermes gateway
initially returned the earlier semantic schema even though a fresh
stdio client listed the new names. Parking and restoring only the
`furbomek` MCP registration caused the gateway to reload the schema.
The rendered profile file was restored byte for byte.

Active completed in the initial Hermes session. Two subsequent
agent sessions called the actual enrolled `furbomek` action tool
sequentially, at 3.0 and 3.75 mm per 20 ms update. Each session
completed a five-second hold and one bounded forward step at low,
high and middle. All twelve receipts reported
`completed_and_disarmed`. Both cameras covered each complete
tool-call interval. The admitted idle voltage was 6.74 V for
the ordinary pass and 6.73 V for the faster pass.

| Height | 3.0 mm per update | 3.75 mm per update |
| --- | ---: | ---: |
| Low | 20 px forward | 18 px forward |
| Middle | 21 px forward | 18 px forward |
| High | 19 px forward | 22 px forward |

Side-view estimates use the median image-plane displacement of five
chassis patches in frames before and after each step. Sampling
during each hold gave zero pixels of median chassis drift on both
image axes. These values describe this camera view and table.
They provide no calibrated travel distance or continuous-gait
qualification. The final middle step verified DISARM. Both
recordings and the complete agent receipts remain private.

### Continuous walking candidate

The six `table_walk_*_continuous` and
`table_walk_*_continuous_fast` semantic actions select a single
guarded three-cycle operation at the named tabletop height. The
last cycle ends with the normal verified DISARM. The host allows
six seconds for completion inside the existing eight-second edge
admission, and the existing local allowlist governs access. A
fresh profile connection must advertise these names before the
powered Hermes trial. Live acceptance requires camera-observed
travel through all three cycles at both speeds and at every
height. A completed receipt alone cannot establish that travel.

At handoff the operator confirmed physical POWER OFF with the body
USB unplugged. The Mac still held the handheld and reported
`read_only_bench` with powered motion admission false.

The local `require_kinect_lock_for_motion` option requires the owned tracker
to report both a fresh frame and a Furbomek lock. Loss cancels motion and puts
the bridge back in read-only state. This option defaults off for the supported
bench, where an operator or a separate private camera may be observing. A
tracker lock is observation only. It provides no calibrated clearance,
stopping envelope or unattended motion qualification.

## Camera, OBS and public activity

The Mac edge owns Kinect capture, the tracker and the Godot viewer. The
remote profile can start and stop the group, query fresh tracker health,
and request RGB, crimson or measured XYZ. The private OBS collection
`Furbomek Mac Test` loads the project-owned [Lua adapter](../../tools/kinect2/obs-edge.lua).
The adapter binds the single named, muted Godot window in the dedicated
scene. It reports frontend recording and streaming state and accepts
Twitch starts only with the private bandwidth-test setting and key suffix.
An accepted streaming start can report `starting`. A stop reports
`obs_stop_requested` as soon as OBS queues it. Confirm the encoder's actual
state through a subsequent status call in both cases.
The agent leaves Twitch credentials in the local OBS profile.

The reverse SSH session also runs the existing Brodex activity broker
against the real profile observer spool. It persists the broker checkpoint
on Brodex and forwards only the redacted public text and timeline. The Mac
checks the schema, sequence and TTL before publishing to Godot. Desktop
images, arbitrary URLs and raw tool arguments or results are outside this
channel. The HUD clears when the tunnel disconnects and the renderer also
expires stale events.

## Observed transport checks

- The Mac LaunchAgent started and re-established activity delivery after a
  graceful reload. Brodex's forwarded socket was owned by the account and
  had mode 0600.
- The dedicated profile discovered seven tools. They started the native
  Kinect workers, returned a fresh object lock and bound the Godot window
  in the existing OBS test scene. Brodex verified OBS recording start and
  stop through the frontend.
- Brodex read DISARMED, no fault, and reported 0.0 V over the real RF bridge
  while the operator confirmed physical POWER OFF. A powered action was
  refused during the read-only window. The forwarded socket rejected an
  attempted local operator request.
- The operator confirmed stillness on power-up and during the local
  ARM-only check at 8.22 V. One separately authorized `active` command
  from the actual Brodex profile MCP entry completed and verified DISARM
  in 781 ms at reported 8.21 V. The operator confirmed physical POWER OFF
  and reported that the visible movement was unclear. The bench expired
  before final telemetry and the local close command confirmed it was
  closed. The test sent no second action or terminal STOP. The
  [installed firmware record](../hardware/firmware.json) retains the prior
  verified image identities.
- A real Hermes chat on Brodex invoked the exact camera and OBS tools.
  Its live thinking and acting state and redacted timeline appeared in
  the private OBS program during the switch from crimson to measured XYZ.
  The 25.8-second 1920×1080 / 30-fps H.264 recording decoded end to end.
  Its SHA-256 is
  `e40085a1cfe024f5d649d793b563317078bdd35b0e91061d49622f1cef801a97`.
- Brodex sent a private Twitch test start and stop through OBS, then
  verified active and stopped state with separate calls. OBS logged a
  successful ingest connection and 110 frames in the final short test.
  Brodex stopped the camera group after verifying the stream had ended.
  The LaunchAgent and relay remain active for on-demand use.
- The gateway suite passed 126 tests, including forwarded socket admission,
  stale start, client disconnect, ARM-only and failed-DISARM checks. Ruff
  and configured type checks passed on the gateway and the activity relay.

## Persistent bridge follow-up

The Mac LaunchAgent was reloaded after checking that the robot bridge,
Kinect, OBS recording and Twitch output were idle. The restarted Mac and the
re-established Brodex forwarding socket both reported `local_bench_closed`.
This confirms a clean startup and the restored route. The deployed software
did not open the handheld, arm, move or flash the robot during this rollout.

The 134-test gateway suite passed, including a pseudo-terminal run of all
eight actions on one bridge, the two forward phases, a silent robot at
preparation, a controller reboot, request contention, admission expiry, and
tracking or tunnel loss during a pending motion. The separate production
candidate passed 43 offline sequence and motion contract tests. These test
wire behavior and playback, with live tabletop motion evidence in
[the motion map](macos-tagless-tabletop-map-2026-11-20.md).

The installed firmware hashes are in
[the firmware record](../hardware/firmware.json). This follow-up only loaded
gateway source. The loaded `edge_robot.py` SHA-256 is
`bbdef6f2cd7c71354731982c03a29b017c26cfe295fec70349bf9a3bde14a402`.
The owner’s last reported physical state was ON. The next hardware pass
needs its initial off-state USB preparation. The supervised scope remains
separate from qualified autonomous stage motion.

## Expressive motion enrollment

On 2026-11-21, the Mac added `poke`, `defensive_brace` and
`tuck_preview` to the local supervised allowlist. The existing Brodex
`furbomek` MCP server exposes the same names on
`robot_perform_action`. The registry entry, reverse socket and tool
set are the existing ones. Hermes's connection check discovered all
seven tools. The registered MCP server's action schema and a forwarded
capabilities call agreed on the three names and a read-only window.

The Mac loaded this change with POWER OFF and the media workers idle.
The prepared handheld remains open while the operator arranges the
tabletop trial. The local ARM-only admission is still required before
motion, with the existing per-move and per-window limits. The
[supported motion retest](macos-expressive-motion-r2-2026-11-21.md#supported-powered-retest)
records the most recent physical evidence until the tabletop trial runs.

### Supervised bare-table pass

The operator confirmed the untethered robot was still on the clear bare
table at power-on and stayed at POWER. ARM-only completed with verified
DISARM at 8.09 V. The 30 fps Logitech recording stalled before motion.
The camera restarted at 15 fps while the Mac kept the USB/RF bridge open.
The first motion window expired between Poke and Brace. The Mac ran a
second ARM-only check on the same bridge and continued on the same power-up.

All four commands used the `robot_perform_action` tool from the actual
registered Brodex `furbomek` MCP server. Each completed and verified normal
DISARM. No motion command was retried.

| Action | Brodex MCP round trip | Video position | Logitech observation |
| --- | ---: | ---: | --- |
| Active | 1.87 s | 00:15 | Legs visibly extended and the chassis settled. |
| Poke | 1.57 s | 00:40 | The moving foot was too obscured to score the reach from this angle. |
| Defensive Brace | 3.05 s | 01:21 | The legs visibly repositioned and returned. Near-front image travel peaked around 7 px. |
| Tuck preview | 3.19 s | 01:40 | The legs visibly moved through the tuck and returned. Near-front image travel peaked around 9 px. |

Round trips include the Brodex tunnel and local Guard lifecycle. The
existing time budgets stayed in force. The Logitech image-plane scores
use scene-corrected local feature tracking. They describe one tabletop
trial, with final chassis drift of about one pixel and no metric scale.
The motion window expired normally. The regular Mac gateway still held
USB and reported `read_only_bench`, with powered actions unavailable.
RF status reported DISARMED, idle and fault 0.

| Private evidence | SHA-256 |
| --- | --- |
| `hermes-powered-table-15fps.mkv` | `c5f68441330425ef2ae94149f11a7ba5ec60251eac0e39a0c7b9ef1651adb0e8` |
| `hermes-mcp-pass.jsonl` | `54507383f9ba803ba2f717159d4c55c15a00ee2c5ffaaa80aa2b7f93d9bda505` |

### Kinect front-view poke repeat

The low front Kinect view exposed both front foot regions. The operator
confirmed they were still at POWER and authorized one repeat. The Mac
enabled another window on the held USB connection. The same Hermes tool
completed Poke in 1.55 s round trip and verified DISARM. The capture saved
210 synchronized optical file and sequence pairs while observing the move.

The left-side foot region in the camera shifted about 4 px sideways at
peak, settling about 3 px sideways from the starting image. The upper
chassis remained nearly stationary. The low view provides evidence of a
small physical response, with the intended lift and forward reach still
unconfirmed. Poke remains an available supervised command whose exact
visual execution needs further qualification.

After the repeat, the temporary Kinect capture stopped. The window
expired and the regular Mac gateway still owned the open handheld.
Capabilities denied powered actions in `read_only_bench`, and the
robot again reported DISARMED, idle and fault 0. No power or USB cycle
was required after the first power-on.

| Private repeat evidence | SHA-256 |
| --- | --- |
| `kinect-poke-evidence.mp4` | `08a339b7299508f71a71a06b2178eb9e4844a81240ef9a1bb7e456d42a268140` |
| Repeat `mcp.jsonl` | `acbb14e72a1e220e6f4eb44a2c54befb18cd5b0d226322e578caf0275e08a56e` |
| Repeat `frames.jsonl` | `88dcbd6fdd66e0900ac6ba69c846751fce226103a9d1571a439be66dfb8aa816` |

For rollback, close the bench and stop test output before unloading the
Mac LaunchAgent. Remove only its script entry from the dedicated OBS
collection. Restore the prior Chezmoi entry from the private Brodex edge
rollback directory, render only the dedicated profile and reconcile its
MCP registration. The device link should remain closed unless there is a
fresh local operator session.
