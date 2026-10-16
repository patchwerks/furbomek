# Furbomek stock Wi-Fi MCP adapter

Hermes's native MCP client invokes the existing robot's Wi-Fi protocol through
this typed stdio adapter. The Freenove controller, installed firmware, handheld
remote and servo/gait code are preserved. This is **not a movement-capable
gateway**: stock reads work; motion requests are explicitly rejected before any
socket access while local TTL/watchdog/preemptive STOP remain unqualified.

## Actual tools

| Server tool | Behavior |
|---|---|
| `robot_get_state` | Stock echo; does not infer motor power, position or physical stop |
| `robot_get_supply_voltage` | Controller-reported ADC encoding, not calibrated battery/cutoff evidence |
| `robot_get_capabilities` | Reports existing stock protocol and the adapter's current limits |
| `robot_request_motion` | Validates a bounded request and returns `rejected`, `sent=false`, `network_accessed=false` |

There is no fake STOP, raw frame, GPIO, shell, calibration, firmware-write or
arbitrary-endpoint tool. No motion packet encoder is implemented. This is a
tool-level boundary, not an OS sandbox; existing Hermes terminal permissions
were not changed and must not be used to bypass the actuation gate.

## Deployed Hermes integration

The Brodex default Hermes configuration has an enabled stdio server named
`furbomek`, with an explicit four-tool allowlist and sampling disabled. The
operator-local endpoint file is `~/.config/furbomek/robot-gateway.json`, mode 0600.
The server entry and a comment-preserving Chezmoi modifier are governed privately;
the full Hermes configuration and credentials are not copied into source control.

Hermes v0.22.0 discovers the server with:

```bash
hermes mcp test furbomek
```

The live tool registry on this installation uses names such as
`mcp__furbomek__robot_get_state`. For a restricted fresh CLI session, select the
configured server name with `--toolsets furbomek`, not the internal
`mcp-furbomek` toolset name. No running gateway was restarted; existing sessions
are not claimed refreshed. See the [live integration record](../../docs/operations/hermes-robot.md).

## Run and validate

From the repository root, Hermes launches this stdio command (not an interactive
terminal UI):

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

Tests use real ephemeral localhost TCP fixtures and real SDK stdio clients,
including malformed/fragmented responses and motion denial. The Hermes enrollment
modifier uses SafeLoader node composition without executing YAML constructors,
rejects ambiguous/merged/unowned target mappings, and changes only its marked
server entry while retaining all other configuration bytes/comments.

The connect/read timeout starts after request-lock acquisition; Hermes's outer
tool timeout also bounds queued calls. This is not a qualified real-time safety
deadline. Live robot reads, fixture tests and physical movement qualification are
separate evidence levels.
