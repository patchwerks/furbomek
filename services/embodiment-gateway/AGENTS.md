# Stock Wi-Fi MCP adapter

This service preserves the installed Freenove controller and firmware. It exposes
real stock echo and controller-reported supply reads over a privately configured
TCP endpoint, using Hermes's native stdio MCP client. It does not replace gait
code, flash the controller, or prove physical motor state from an echo.

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
