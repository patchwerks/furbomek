# Stock and guarded robot MCP adapters

The legacy stock backend exposes TCP echo/supply without actuation. The separate
guard backend uses the programmed handheld's UART/RF bridge and is deployed only
in Hermes's `furbomek` profile. This service never flashes boards or exposes raw
serial, GPIO, reset or arbitrary actuator operations as model tools.

- Do not expose raw frames, serial, GPIO, arbitrary endpoints or shell execution
  as model tools. Endpoint settings are operator-local JSON, not tool arguments.
- The stock backend is read-only. Motion requests return an explicit rejection
  before opening a socket. Do not add a configuration switch that pretends the
  unqualified stock path has robot-local TTL/watchdog/preemptive STOP.
- Do not implement a fake STOP by substituting sleep, calibration or install
  state. Do not claim a requested/acknowledged action physically happened.
- Preserve the operator-confirmed rigid bench support; do not repeat camera,
  identification or USB setup unless there is evidence the arrangement changed.
- Use `uv run --frozen pytest -q`, Ruff, formatter checks and basedpyright. Real
  localhost wire/stdio tests are distinct from live robot or Hermes execution.
- Keep private endpoint settings, full Hermes configuration, credentials, live
  camera frames, logs and `.venv` outside project Git. The Chezmoi overlay owns
  only its marked `mcp_servers.furbomek` entry and preserves unrelated text.

## Guard serial adapter

`serve-guard` is a separate, operator-local UART MCP process with motor-off and
explicit supervised powered modes. It must never widen the stock `serve` server,
`GatewaySettings`, `create_server`, or the stock four-tool enrollment. The model
receives no serial path, frame, endpoint, reset, rearm, or arbitrary action
argument. The sole motor-off check is bounded and must gate on a Guard-reported
sub-3 V supply reading; that reading is not independent proof of motor power.
The separate `supervised_powered_bench` mode exposes only the closed semantic
`robot_perform_action` tool. It requires the operator-present supported-chassis
profile, fresh 6.5-8.6 V supply, and an explicit `qualified_actions` tuple whose
default is `("active",)`; it never enables other gaits implicitly. Completed
actions use sequenced DISARM to return to Disarmed without panic STOP. Failed,
cancelled, timed-out, or ambiguous actions use shielded raw STOP. Neither mode
claims physical motion or visual health.
STOP is the actual terminal `80 30 81` primitive, not a sleep substitute. Never
claim physical motion, motor power, or watchdog-reset behavior from the UART.

Keep exchanges capped at 200ms and serialize non-STOP operations for the whole
check. STOP bypasses that operation gate and cancels the active scope; shield
both STOP delivery and active-state cleanup. Preserve partial receive bytes
across cancellation, and handle valid unsolicited completion/duplicate STOP
replies without accepting stale command acknowledgements. Completion requires
Armed, no fault and busy=false, never merely non-busy Fault. The 92-test suite
includes actual PTY wire and MCP stdio lifecycle regressions. Do not replace it
with parser-only mocks or silently widen the motor-off profile.

Current deployment enrolled all8actions only after40 motor-off cycles, recorded
native powered checks and actual powered Hermes acceptance. Normal completion
must return a sequence-bearing DISARM ACK and reset_required=false; emergencies
remain Fault/reset-only. Only KEEP/STATUS may retry identical packets once on
timeout; result10 marks fresh duplicate-query ACKs without lease renewal. Never
retry mutations. Poll one heartbeat ACK per cycle and include planned sleep,
ceiling-rounded elapsed time and clock/disarm margins in lease-budget checks.
Do not turn the supported bench acceptance into a floor/autonomy or mechanical
repair claim; retain the rear-right report's exact method scope.

## Agent-owned reset recovery, not a model reset tool

With recovery authorized, a trusted host maintenance agent can reset the robot
controller through the existing robot USB DTR link after fresh user confirmation
that physical POWER is OFF. This was actually done after the powered acceptance;
RF STATUS verified BOOT/sequence0/fault0/notbusy. Do not ask the user to locate or
poke RESET pins when this safe USB recovery is available. Ask for physical help
only when the USB link is unavailable, inaccessible, or unsafe. Never infer POWER
OFF from supply telemetry or a previous session's confirmation.

Keep this outside the MCP runtime: no reset tool, automatic fault clearing,
retry-by-reset, or automatic post-reset motion. Coordinate exclusive access with
the current controller owner; see `docs/operations/hermes-robot.md` for procedure.
