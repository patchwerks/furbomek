---
created: 2026-10-29T16:50:01Z
branch: work/4-simulation-lab
author: Codex
status: active
---
# Offline Simulation Lab

Follow root guidance and issue #4. This directory owns test-only harnesses and
verification discovery. It is not a robot or speech runtime.

- Compile only explicit, reviewed pure native source lists. Never link AVR
  adapters, vendor gait libraries, serial clients or live service launchers.
- Use virtual time and in-memory transport/sink fixtures; never open real devices,
  sockets, OBS, cameras or Hermes profiles. Do not install tools from this runner.
- Run on disposable credential-free workers with network and device access denied.
  A clean environment alone is not an isolation boundary.
- Preserve canonical policy source and existing suites. A fixture failure is a
  failure; do not replace the policy with an easier simulated implementation.
- Report source hashes, toolchain identity, precise evidence tier and missing
  gates. Protocol callbacks are not physical motion or cutoff measurements.
- Speech/PCM cancellation tests must consume the accepted canonical contract.
  Never invent a parallel audio clock to complete a test matrix.
