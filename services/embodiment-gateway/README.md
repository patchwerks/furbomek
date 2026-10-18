# Furbomek stock and guarded robot MCP adapters

The legacy `serve` backend remains read-only stock Wi-Fi with motion denied before
I/O. The deployed `serve-guard` backend connects Hermes's dedicated `furbomek`
profile to the USB handheld bridge and robot-local RF guard. It exposes state,
radio supply telemetry, actual STOP and repeatable powered semantic actions in
`supervised_powered_bench` mode. The eight enrolled commands passed native and
actual Hermes powered acceptance on the supported robot. This is not floor
locomotion, per-leg/raw control or unattended-operation qualification. The old
motor-off check remains a separate mode for operator diagnostics.

## Legacy stock tools (`serve`, not the current robot profile)

| Server tool | Behavior |
|---|---|
| `robot_get_state` | Stock echo; does not infer motor power, position or physical stop |
| `robot_get_supply_voltage` | Controller-reported ADC encoding, not calibrated battery/cutoff evidence |
| `robot_get_capabilities` | Reports existing stock protocol and the adapter's current limits |
| `robot_request_motion` | Validates a bounded request and returns `rejected`, `sent=false`, `network_accessed=false` |

There is no fake STOP, raw frame, GPIO, shell, calibration, firmware-write or
arbitrary-endpoint tool. No stock motion packet encoder is implemented. This is a
tool-level boundary, not an OS sandbox; existing Hermes terminal permissions
were not changed and must not be used to bypass the actuation gate.

## Separate motor-off Guard adapter

`serve-guard` is a different stdio MCP server. It does not alter the stock
server, its four-tool allowlist, or its TCP settings contract. Its exact private
JSON settings schema is:

```json
{
  "bridge_device_path": "/dev/ttyACM0",
  "mode": "motor_off_bench",
  "operator_profile": "operator_confirmed_motor_off_bench",
  "exchange_timeout_seconds": 0.2,
  "active_check_timeout_ms": 2000,
  "automatic_robot_reset_enabled": false
}
```

`exchange_timeout_seconds` is `>0` and `<=0.2`; `active_check_timeout_ms` is
`>0` and `<=2000`. The motor-off Guard tools are `robot_get_state`,
`robot_get_supply_voltage`, `robot_get_capabilities`, `robot_stop`,
`robot_run_motor_off_check`, and `robot_perform_action`. The motor-off check
accepts no arguments and sends only constrained Active after a fresh supply read
below 3 V and the fixed operator profile. That gate is conservative but not
independent proof that motor power is off. Every attempted check sends terminal
STOP during cleanup; no tool resets or rearms a Faulted robot. Results report
physical motor state as unknown and physical observation as false.

`robot_perform_action` is always listed but refuses before BEGIN unless the mode
is powered, the profile is `operator_present_supported_chassis`, the fresh
supply is 6.5-8.6 V, and the action is in the explicit settings allowlist. In
powered mode the motor-off tool is not registered.

## Supervised powered bench settings

The private operator JSON schema is closed and contains no tool-supplied
endpoint, timing, reset, speed, duration, repeat, leg, raw-frame, or firmware
arguments:

```json
{
  "bridge_device_path": "/dev/ttyACM0",
  "mode": "supervised_powered_bench",
  "operator_profile": "operator_present_supported_chassis",
  "exchange_timeout_seconds": 0.2,
  "active_check_timeout_ms": 2000,
  "action_timeout_ms": 2500,
  "qualified_actions": ["active"],
  "automatic_robot_reset_enabled": false
}
```

The eight closed action names are `active`, `sleep`, `forward`, `backward`,
`left`, `right`, `turn_left`, and `turn_right`. The default allowlist contains
only `active`; additional actions require explicit operator enrollment after
qualification. The host timeout remains at or below 2500 ms and the board
operation limit remains 3 seconds; no timing increase is made here.

An accepted action state-syncs from BOOT or Disarmed, uses a fresh 8-byte
correlation identifier (correlation only, not authentication) and globally exact
21-bit sequence, stages ARM, sends one semantic
EXEC, polls one KEEPALIVE ACK containing state/busy at about100ms, then sends DISARM and requires
the standard sequence-bearing Disarmed/fault-0/busy-0 acknowledgement. A completed action does
not send panic STOP, so a second action and a fresh service process can start
from Disarmed. Cancellation, timeout, transport/protocol failure, bad DISARM
acknowledgement, or explicit `robot_stop` uses shielded raw STOP. STOP remains
reset-only and terminal until physical reset; no tool clears or rearms it.
Results report protocol facts only and cannot
claim new visual, mechanical, or physical health.

Run it only through the private settings file:

```bash
sudo -n -u "$(id -un)" -g dialout "$HOME/.local/bin/uv" run --frozen \
  --project services/embodiment-gateway furbomek-gateway serve-guard \
  --settings "$HOME/.config/furbomek/robot-guard.json"
```

## Deployed Hermes integration

The existing `furbomek` profile has the enabled guarded server, powered operator
mode and all eight actions explicitly enrolled after qualification. Session
`20261017_115945_c654b1` executed each once and received completed/disarmed with
`physical_reset_required=false`; final explicit STOP verified Fault4. Recorded
camera evidence confirms visible supported gait/posture changes separately from
the API's deliberately conservative physical-observation fields.
The default profile's entry is disabled: unrelated long-lived chats otherwise
open the same exclusive UART and prevent the robot profile connecting. No other
session, draft or provider setting was interrupted. Private settings are
`~/.config/furbomek/robot-guard.json`; the bridge uses a stable USB-port path.
Only this MCP child receives the existing `dialout` group through scoped sudo;
no user groups, udev, firewall or network profiles changed. Chezmoi owns only
named MCP blocks and adapter settings, not full credential-bearing configs.

Hermes v0.22.0 discovers the server with:

```bash
hermes -p furbomek mcp test furbomek
```

The live tool registry on this installation uses names such as
`mcp__furbomek__robot_get_state`. For a restricted fresh CLI session, select the
configured server name with `--toolsets furbomek`, not the internal
`mcp-furbomek` name. A real profile session invoked all five tools on 2026-10-17:
BOOT, supply 1.56 V, motor-off Active completed in 1.119 s, STOP verified and final
FAULT/code4. POWER stayed OFF; this is not new powered-motion acceptance. STOP
requires physical reset before another action; no tool automatically resets the
robot. See the [live integration record](../../docs/operations/hermes-robot.md).

## Agent-owned USB reset recovery

A trusted host maintenance agent can deliberately reset the robot controller
over its existing USB DTR link, with authorized recovery and fresh user-confirmed
physical POWER OFF. This cleared the acceptance-test latch and RF STATUS verified
BOOT/sequence0/fault0/notbusy. Agents should handle this recovery rather than ask
the user to find RESET unless USB recovery is unavailable or unsafe. Coordinate
exclusive device ownership first. This is not an MCP reset tool, automatic fault
clearing, or permission to resume movement. See the
[recovery procedure](../../docs/operations/hermes-robot.md#agent-owned-usb-reset-recovery).

## Run and validate

The retained legacy stock backend can still be launched from the repository root
with its separate TCP settings (it is not the current robot profile's backend):

```bash
uv run --frozen --project services/embodiment-gateway furbomek-gateway serve \
  --settings "$HOME/.config/furbomek/robot-gateway.json"
```

The public `settings.example.json` is loopback-only for fixtures, not the robot's
live configuration. Endpoint settings cannot be supplied through tool arguments.

From this service directory:

```bash
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen basedpyright
uv lock --check
```

The 92 tests include stock TCP, real PTY UART and MCP stdio cases covering
concurrent STOP, external cancellation, partial replies, disconnects, false
completion, duplicate replies and motor-off voltage refusal. The Hermes enrollment
modifier uses SafeLoader node composition without executing YAML constructors,
rejects ambiguous/merged/unowned target mappings, and changes only its marked
server entry while retaining all other configuration bytes/comments.

The connect/read timeout starts after request-lock acquisition; Hermes's outer
tool timeout also bounds queued calls. This is not a qualified real-time safety
deadline. Live robot reads, fixture tests and physical movement qualification are
separate evidence levels. Only KEEP/STATUS timeout acknowledgements may be
retransmitted once with identical bytes; fresh replay ACKs are tagged result10
without renewing lease or sequence. Motion and session mutations are never
retried. Conservative remaining-lease checks include elapsed time,10ms clock
quantum, planned sleep and the30ms disarm margin. One unchanged legacy TCP
serialization fixture flaked once under load and passed isolated/full reruns;
it was neither weakened nor disabled.
