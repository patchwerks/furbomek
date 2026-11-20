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

Only the Mac agent's separate local operator socket can prepare, enable or
close a bench window. Begin with fresh physical POWER-OFF and charger
isolation confirmation. The agent opens the identified handheld bridge,
checks healthy idle state and the reported off-state voltage, then permits
telemetry for up to ten minutes. Confirm chassis support with all legs
free and operator presence at the physical cutoff before power-on. Verify
stillness at power-on. The local enable transaction checks supply and runs
ARM-only with verified DISARM before making the eight already qualified
actions available for up to two minutes. Observe ARM-only before requesting
the first movement. The robot and handheld retain the installed protocol
and local watchdog. Serial ownership and bench authority end on expiry,
operator close or tunnel loss. Terminal STOP preserves the installed
fault latch and has priority over queued work.

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

For rollback, close the bench and stop test output before unloading the
Mac LaunchAgent. Remove only its script entry from the dedicated OBS
collection. Restore the prior Chezmoi entry from the private Brodex edge
rollback directory, render only the dedicated profile and reconcile its
MCP registration. The device link should remain closed unless there is a
fresh local operator session.
