# Private media-session lifecycle

Read root guidance, the module README and `docs/operations/kinect2-host.md`.

- One session owns capture/tracker/broker/viewer/OBS under `host-session.lock`.
  Do not run a second camera owner or kill unrelated chats, windows or processes.
- READY requires current-launch producer data, live workers and successful owned
  OBS configuration. A process-active unit or recording request is not acceptance.
- Clean viewer/OBS exit ends the whole managed session; crashes use bounded
  restart windows. Keep signal, timeout, backoff and descendant cleanup tests real.
- Finalize requested recording before generic OBS termination; target only the
  owned OBS PID/window and verify the resulting file in live acceptance.
- Keep the host unit parent-first (`KillMode=mixed`) so cgroup teardown does not
  defeat recording cleanup. Manage host config with Chezmoi; never embed secrets.
- Screens are off; unqualified live desktop policy must fail before any worker
  or desktop startup. No public broadcasting, robot reset, head actuation or raw
  model controls belong here. Preserve the selected Hermes/jabberWERK authority.
- Run locked tests, strict checks and root `tools/verify-media.sh`; source fixtures
  do not replace actual private recording and lifecycle qualification.
