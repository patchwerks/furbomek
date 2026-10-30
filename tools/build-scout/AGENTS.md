# Build Scout boundary

Canonical work: <https://github.com/patchwerks/furbomek/issues/14>.
Follow the root guide and shared tracker. This directory owns advisory developer
tooling only; it has no product runtime, dispatch, robot or media authority.

`collect.py` is a trusted operator-side GET-only collector. Review it before use
with credentials. Never run candidate code/tests with credentials; test it with
mocked subprocess responses in a worker denying network, host-home and devices.
`scout.py` performs offline analysis only. Keep its import tree free of collectors,
network clients, subprocesses and runtime adapters. Collected snapshots and derived
reports may contain private metadata: keep them outside the repository and never
publish them automatically. Synthetic test fixtures contain no real private data.
