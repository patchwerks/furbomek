---
created: 2026-10-29T16:50:01Z
branch: work/4-simulation-lab
author: Codex
status: active
---
# Simulation Lab: offline native boundary fixtures

References [verification issue #4](https://github.com/patchwerks/furbomek/issues/4).
This first slice runs deterministic transport-failure and command-boundary
scenarios against the existing **real** Guard/Dispatcher policy implementation.
It also runs the existing Guard and actuator-disabled diagnostic native suites.
No firmware, runtime policy, deployment configuration or existing media gate is
changed. This is a partial contribution to #4; it does not close that issue.

## Run and evidence

On a disposable, credential-free worker with network and device access denied:

```sh
python3 tools/simulation-lab/run.py --inventory
python3 tools/simulation-lab/run.py
python3 -m unittest discover -s tools/simulation-lab -p 'test_*.py' -v
```

Requires Python 3.10+ and a native C++17 compiler. Use `--cxx /path/to/compiler`
for an installed compiler. No dependency installation or download occurs.
`--suite guard-scenarios`, `--suite guard-regression`, and
`--suite diagnostic-regression` select individual suites; repeat to combine.
Default runs all three. Compiler warnings are errors; each compile has a
60-second timeout and each executable a 30-second timeout.

JSON output includes each suite's status, compiler identity and SHA-256 source
and header manifest. Build products and a blank HOME are temporary and removed
on exit. Child environments exclude credentials; this is environment hygiene,
not an operating-system sandbox. The runner must still run in the isolated
worker described above. It has no credential discovery, socket, serial, reset,
firmware-write or service-start functionality.

Exit 0 means the selected offline suites passed (or inventory completed); exit 1
means a selected suite failed or could not execute; exit 2 means the compiler is
missing or arguments are invalid. `other_gates` remains explicit even when the
native subset passes. Save the JSON with the reviewed commit as verification
evidence outside the checkout; inspect it before publication.

## Scenario coverage

| Scenario | Actual implementation exercised | Assertion |
| --- | --- | --- |
| Command boundaries | Guard codec and dispatcher | Eight semantic actions; duplicate/reordered mutations cannot execute twice; invalid action/sequence cannot encode; corrupted CRC faults |
| STOP and cancellation | USB STOP against an RF-owned busy Guard | Lost reply cannot prevent local STOP; stop callback precedes ACK; repeated STOP remains terminal; late completion/work cannot restart |
| Latency and loss | Guard deadlines with explicit virtual milliseconds | 499 ms heartbeat arrives in time; 500/501 ms is too late; lost next heartbeat expires exactly; 32-bit time wrap preserves boundary |
| Lost query ACK | Actual KEEP query replay | Retry reports fresh remaining lease and does not renew it |
| Independent operation limit | Guard operation deadline | Healthy 100 ms heartbeat stream cannot keep a stalled operation alive past 3,000 ms |
| Recovery | Guard normal DISARM and terminal Fault | Normal completion needs next sequence/new session; Fault cannot clear through reconnect, BEGIN or DISARM; fresh fixture never auto-resumes |

The fixtures call the production entrypoints with in-memory encoded RF/USB
messages. They use test-only sinks to count callbacks, not motors or radio
hardware. Virtual time is a controllable input to the existing policy; there
are no sleeps, timing tolerances or wall-clock performance claims. A native
process restart in a fixture does not reset any physical controller.

## Existing gates and limits

[tools/verify-media.sh](../verify-media.sh) remains the locked Python/type/lint
and real Godot consumer gate. Its three service suites, snapshot regression,
Godot fixtures and shell validation are not replaced by these native checks.
The inventory also names AVR builds and legacy npm hooks; it does not silently
execute them or treat their absence as a pass.

Speech cancellation, avatar convergence and the single PCM-derived clock belong
to [#7](https://github.com/patchwerks/furbomek/issues/7), after its broker, Hermes,
speech and licensed-fallback prerequisites. This slice verifies command
cancellation only. It cannot qualify speech interruption, program audio,
physical STOP latency, electrical cutoff, RF propagation, watchdog reset,
installed firmware, robot safety under load, HIL, public streaming or autonomy.
The diagnostic suite's capability bitmap is zero; it is not the installed Guard
and not a robot simulator. Existing hardware evidence remains authoritative.

The paired [Simulation Lab workflow](../../.github/workflows/simulation-lab.yml)
runs this bounded native subset on an isolated GitHub runner. Completing #4 still
requires broader locked media checks and honest treatment of AVR and legacy
build prerequisites, plus actual CI run evidence. Independent review
is required before any merge. Deleting this directory rolls back the tooling;
there is no deployed state to undo.

## Verification record

Base source inspected: `9347304e866ca90e8eec2d85f3bd3c41002d9a42`.
Observed on 2026-10-29: the existing non-live media entrypoint returned exit 2,
`Missing prerequisite: uv`, in an isolated worker. No gate was weakened and no
live system was accessed. Native suite results are recorded after execution in
the accompanying PR evidence.

Observed local runner verification: six runner outcome tests passed in the
credential-free, network/device-denied worker. Local native compilation did not
pass: Clang treats pre-existing CRC shift signedness in both native `frame.cpp`
files and an existing diagnostic test index conversion as errors under the
unchanged strict warning flags. These production files were not changed and
warnings were not disabled. The GCC CI run is the native behavior gate; do not
count local compilation failure as a scenario pass.
