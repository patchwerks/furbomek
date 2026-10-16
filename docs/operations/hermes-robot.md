# Hermes to stock robot: live MCP integration

Verified 2026-10-16 against installed Hermes v0.22.0, source revision
`e06df9c2eae6901f4c88f464e0ae6e753c0428b8`. Read project `AGENTS.md`, current
hardware/firmware records and the [wireless runbook](robot-wireless.md). Agents
operate this integration; do not hand configuration work back to the operator.

## What is implemented, and what is not

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
