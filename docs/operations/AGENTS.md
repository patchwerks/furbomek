# Operations documents are agent runbooks

The user explicitly delegates operational instructions and recovery to agents.
Maintain these documents for future agents, not as homework for the user.

- Read the nearest service/tool `AGENTS.md` and root guide before executing a
  runbook. Route Kinect work through `tools/kinect2/AGENTS.md` and
  `services/camera-capture/AGENTS.md`.
- Keep exact versions, owning source/config paths, launch/stop/recovery commands,
  observed evidence, unverified claims, rollback and governance state current.
- Actually execute applicable non-destructive validation and use the real
  surface. Never call a planned command runnable before testing it.
- Preserve credentials, private media and unrelated user work. Read the host's
  `~/.config/NETWORK.md` before remote-access/network work and follow its managed
  source workflow. Do not reboot or change the physical display path casually.
- Inform the user of results, limits and genuinely required decisions/actions;
  do not respond with a runbook link instead of completing the operation.
