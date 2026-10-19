# Hermes robot MCP integration

## Current deployment: supervised supported powered actions

The operator has authorized supported powered checks and remains at the physical
POWER cutoff. All eight bounded actions passed recorded native powered checks
after40 sequential motor-off cycles. The `furbomek` profile now selects
`supervised_powered_bench` with the explicit qualified allowlist: `active`,
`sleep`, `forward`, `backward`, `left`, `right`, `turn_left`, `turn_right`.
Each direction/turn is one vendor gait quantum, not continuous walking or a
measured travel distance. Actual powered Hermes verification passed below.

### Actual powered Hermes result

Session **`20261017_115945_c654b1`** read Disarmed/8.15V/capabilities and executed
all eight actions exactly once. Each returned `completed_and_disarmed`, accepted,
completed and disarm-acknowledged, with `physical_reset_required=false`. Tool
times were193ms Active,1101 Sleep,2001 forward,1194 backward,1102 left,908 right,
1106 turn-left and996 turn-right. No controller reset occurred between requests.
The final explicit `robot_stop` verified FAULT and final state was Fault/code4,
not busy, requiring deliberate reset. No additional movement was scheduled.

The39.9s private camera recording shows visible posture/gait changes on the
support and still reviewed post-STOP frames. JSONL SHA256:
`b66a78ace2ae3aef2a808487b4579880a4da739fd6d19925b6e96f19911b8942`;
video SHA256:
`6249e64180073aa96788df1cd878f5ec117104abe9df0e580daf4428b1d2a664`.
Files are `hermes-powered-eight-actions.jsonl` in the private enrollment directory
and `hermes-powered-eight-actions.mp4` in the private camera directory recorded
in hardware.json. Do not commit the media, config backups or full transcripts.

**After this acceptance run: turn POWER OFF, leave both USB cables connected.**
The final test intentionally used emergency STOP. After the user confirmed POWER
OFF and could not find the button, the operator cleared that test latch through
the existing robot USB DTR reset and verified BOOT/sequence0/fault0 over RF.
**No additional reset is needed now.** For a future latch, deliberate operator
USB reset with POWER OFF is available while tethered; do not make the user poke
pins or dismantle the robot. The robot controller's button is another option,
not the handheld's reset. Do not expose automatic reset/clear-fault tools.
Normal completed actions no longer need this step; only emergency STOP/faults do.
Keep the robot supported for the currently qualified mode; floor travel and
unattended operation remain unqualified.

`robot_perform_action(action)` replaces the motor-off-only check in this mode.
It requires fresh controller-reported6.5–8.6V plus the operator-present profile,
executes one action with100ms heartbeats and a2.5s host limit, then verifies normal
DISARM. Firmware retains3s operation,500ms link and30s session limits. The next
normal action resumes with a higher global sequence and changed correlation ID,
not a controller reset. This finite ordering is not authentication. Emergency
STOP, unexpected lease loss and faults remain latched; no tool clears them.

Keep the robot on its central support and the operator ready at POWER for this
verification. Floor walking, free roaming and unattended control are not accepted
by these tests. Do not broaden the rear-right restoration report beyond its
specific guarded ARM/Active method.

## Agent-owned USB reset recovery

First follow the [wired maintenance protocol](robot-wired-maintenance.md) for
ownership, charging/isolation and recording requirements. An idle/charging robot
does not authorize a serial open, reset or update.

Recovery belongs to the trusted host maintenance agent, not the user and not
the motion MCP runtime. When recovery is authorized, obtain **fresh user
confirmation of physical POWER OFF** and keep the chassis supported. A prior
session's OFF report or controller supply reading is not sufficient. Coordinate
with the device owner and release any existing port owner normally; never kill
an unrelated session or race another agent for the UART.

The verified procedure used the identified **robot controller USB** port, not
the handheld: exclusive pySerial access at115200 baud, DTR false for100ms then
true, wait2s. After releasing that port, the handheld USB/RF bridge (allow2s for
its startup) returned CRC-validated STATUS: BOOT/sequence0/fault0/busyfalse. Exact
local by-path ports are in `docs/hardware/firmware.json`; recheck identity if
cabling changed. Record the reset and observed result in the hardware records.
Do not send BEGIN/ARM/EXEC, change EEPROM/firmware, or resume movement as part
of recovery. If verification fails, remain stopped and report the failure.

Prefer this agent-operated USB hardware reset over asking the user to find a
button or poke pins. Request physical reset only if USB recovery is unavailable,
inaccessible, or unsafe. No reset MCP tool or automatic fault-clearing loop is
enabled. Normal completed actions need no reset. The most recent verified reset
already cleared the test latch; this procedure is not an instruction to reset
again or evidence of the robot's live state in a future session.

## Previous motor-off verification: guarded USB/RF, 2026-10-17

Use the existing **`furbomek` profile**, not default. Its five-tool server owns
the handheld's exclusive UART. The default-profile hardware entry is disabled:
an unrelated running default Hermes chat auto-loaded it and reserved the device
during initial deployment. Supported config reload removed only that entry;
the chat, its draft and other tools were not interrupted.

Private settings are `~/.config/furbomek/robot-guard.json`. The profile MCP entry
is rendered from `~/.config/furbomek/hermes-robot-mcp.json`, invoking
`serve-guard` with scoped existing `dialout` group access. Chezmoi owns only the
marked blocks in default and robot profile configs, plus non-secret settings.
Both configs were byte-compared against backups with their owned blocks removed;
all other bytes/comments/provider settings remain identical.

```sh
hermes -p furbomek mcp test furbomek
hermes -p furbomek chat --oneshot --format stream-json --toolsets furbomek \
  --max-turns 10 --run-budget 120 \
  -q 'With confirmed POWER OFF, read state, supply and capabilities; run the motor-off check once; STOP; read final state. Do not retry or reset.'
```

Actual session `20261017_055112_0725f7` invoked:

- `mcp__furbomek__robot_get_state`: BOOT, available, not busy.
- `mcp__furbomek__robot_get_supply_voltage`: **1.56 V** over USB handheld/RF;
  explicitly not independent motor-power proof.
- `mcp__furbomek__robot_get_capabilities`: fixed motor-off mode, no auto-reset,
  configured watchdog but reset behavior untested.
- `mcp__furbomek__robot_run_motor_off_check`: completed in **1119ms**, Active
  accepted, busy cleared, STOP written and FAULT acknowledged.
- `mcp__furbomek__robot_stop`: STOP written and FAULT verified.
- Final state: FAULT, code **4**, not busy, physical reset required.

The model reported those facts correctly. Private JSONL evidence is under
`~/.local/state/furbomek/hermes-guard-enroll.boty2A/`; its SHA-256 is
`7fc32644e665ac7ed6d8b5502105ca5c1075b84024ea5b22248e5b2ff391c47d`.
POWER stayed OFF and no powered movement was attempted in this session. The
earlier supported powered Active test is separate evidence, not a Hermes run.

The current firmware adds read-only SUPPLY `0x34 -> 0x35` without arming,
renewing leases, changing sequence or stealing the owner reply route. Both
application writes and unchanged EEPROM comparisons passed. Original private
images and the demonstrated restoration procedure are retained.

Host checks: **66 tests**, Ruff/format, basedpyright zero errors/warnings and UV
lock check passed. Tests include real PTY partial replies, cancellation,
disconnect, concurrent STOP, failed-write truth, unsolicited completion, false
completion prevention and actual MCP stdio action/STOP. CLI help and bad config
input were exercised in tmux. LSP servers remain unavailable as previously
declined; compiler/type-check CLIs were used.

**Leave POWER OFF. No further movement is scheduled.** The check requires
operator-confirmed motor-off mode plus an additional reported-supply gate below
3V. It does not expose walking, per-leg motion, raw frames or reset. A terminal
STOP requires physical robot reset before another action; no model tool does
that automatically. Do not reset or power on merely to clear the test result.

## Historical stock Wi-Fi integration, 2026-10-16

Verified 2026-10-16 against installed Hermes v0.22.0, source revision
`e06df9c2eae6901f4c88f464e0ae6e753c0428b8`. Read project `AGENTS.md`, current
hardware/firmware records and the [wireless runbook](robot-wireless.md). Agents
operate this integration; do not hand configuration work back to the operator.

### Historical stock implementation, superseded by the current deployment above

The default Hermes profile now has a native stdio MCP server `furbomek` invoking
[`services/embodiment-gateway`](../../services/embodiment-gateway/README.md).
It uses the existing ESP8266 Wi-Fi and installed Freenove controller firmware.
No board, remote, gait code, servo wiring, calibration or firmware was replaced.

The adapter provides live stock echo and supply reads. **Movement is not enabled.**
`robot_request_motion` is a policy-request interface that returns an explicit
rejection before network access; it is not a successful leg test or a queued
movement. No STOP tool is advertised because a qualified stock stop primitive is
not available. Do not substitute sleep/install/calibration for emergency STOP.

Do not interpret the eventual autonomy requirements as a mandate to discard the
working controller or rewrite all its gait code. Preserve and integrate the stock
stack. Qualifying a local failsafe can involve a targeted change or an independent
robot-mounted gateway; neither has been accomplished by installing this MCP
adapter. The reported rear-right-leg symptom remains undiagnosed.

## Deployment and credential preservation

- Runtime: independently locked UV project, MCP SDK 1.27.1, Pydantic v2, AnyIO.
  Hermes's own PM environment and core source were not modified.
- Private endpoint settings: `~/.config/furbomek/robot-gateway.json`, mode 0600.
  No endpoint or raw-frame parameter is exposed to the model.
- Private non-secret MCP entry: `~/.config/furbomek/hermes-mcp.json`, rendered
  from Chezmoi. It selects the four named tools, disables server sampling and
  supplies bounded tool/connect timeouts.
- Chezmoi `modify_private_config.yaml.tmpl` owns only the marked
  `mcp_servers.furbomek` block. Full provider/user settings were not enrolled.
  Immediately after enrollment, removing the three owned lines produced a
  byte-for-byte match to the privately preserved original config. Comments,
  other MCP entries and provider settings survived unchanged.
- Existing config backup, preview diff and live JSONL evidence are private under
  `~/.local/state/furbomek/hermes-enroll.*/`, not project Git.
- No network listener, firewall or route was added. Ethernet remains Internet/
  Tailscale, Wi-Fi remains robot traffic. Keep Ethernet connected.

## Verification through the actual Hermes surface

`hermes mcp test furbomek` connected over stdio and discovered all four tools.
Then a fresh Hermes session selected **the configured server name**:

```sh
hermes chat --oneshot --format stream-json --toolsets furbomek \
  --max-turns 4 --run-budget 90 \
  -q 'Call only the robot state and supply-voltage tools. Do not request motion.'
```

The observed runtime names were:

- `mcp__furbomek__robot_get_state`: successful tool result, `connected=true`,
  `stock_echo_validated=true`; motor-power/position knowledge and qualified STOP
  flags remained false.
- `mcp__furbomek__robot_get_supply_voltage`: successful tool result,
  controller-reported **1.55 V**, explicitly not calibrated or independent power
  safety evidence. Do not diagnose battery charge or switch state from this value.

The final agent reply reported these tool results. **Evidence is the actual
tool-result events, not merely CLI exit zero.** An initial attempt using the
internal selector `--toolsets mcp-furbomek` exited zero but reported unavailable
tools; correcting the selector per the installed CLI resolved it. Do not repeat
that failed selector or claim the first run was a successful invocation.

Fresh-session execution is verified. No existing gateway/session was restarted
or forcibly reloaded. Existing sessions may need their supported `/reload-mcp`
flow or a new session; do not silently invalidate ongoing prompt caches.

## Checks and boundaries

The service suite passes 38 tests, Ruff, formatter checking, basedpyright with
zero errors/warnings, and the UV lock check. Tests include real TCP fragmentation,
invalid frames, timeout/refusal, real MCP stdio calls, bounded input rejection and
configuration ownership/preservation. YAML whitespace, escaped-key, explicit-key
and merge ambiguities were reproduced as failing tests before adding parse-only
semantic preflight. Live stdio startup was independently tested by Hermes.

This does not establish motion, leg calibration, safe power removal, a local
watchdog or an OS sandbox. Existing terminal privileges were not changed. Never
use a shell/socket workaround to make the model appear to have qualified motion.

## Targeted rollback

Preserve current unrelated config. Set only `enabled` to `false` in the privately
managed MCP-entry source, then apply that JSON target and the Hermes config target
with Chezmoi. This disables only this server on the next supported session/reload;
it is not a motion-enable flag. The disabled rendering and preservation of sibling
servers are covered by a regression test. The live deployment remains enabled;
disabling it was not performed during QA.

Do not destroy the entire `.hermes/config.yaml` target or restore an old full
backup over later user changes. If permanently retiring it, first disable this
owned entry, then deliberately retire only its modifier/settings rather than the
whole user config. No robot firmware restoration is necessary: no device memory
changed.
