# Wired device maintenance during downtime

Status: agent operating protocol, 2026-10-18. This is not permission to flash,
reset, energize or move hardware merely because a robot is idle or charging.
Agents perform the technical work; ask the user only for physical conditions,
authorization or actions that cannot safely be performed from the host.

## 1. Choose the maintenance tier

| Tier | Permitted work | Required gate |
|---|---|---|
| Software only | Edit, native/PTY tests, AVR builds, review, documentation | Isolated worktree; no device opens, live MCP startup or host config changes |
| Wired telemetry/reset | Verified read-only requests or deliberate controller reset | Designated operator, authorized recovery, fresh physical POWER-OFF confirmation and verified isolation; opening serial can reset a board |
| Application update | Program a reviewed application-only artifact, verify and roll back if needed | All preceding gates plus preserved/verified current images, reproducible candidate, exact board/port mapping and tested recovery method |
| Powered acceptance | Staged ARM and explicitly selected bounded actions | Separate authorization, supported chassis/legs free, operator at physical POWER cutoff; never implicit in an update |

Charging is **not** a fifth authorization tier. The archived
[V3 battery guide](../hardware/vendor/freenove/battery/AboutBattery_for_V3.pdf)
(About Battery, PDF page2) says USB does not charge the cells; use the appropriate
separate charger and vendor charging procedure. Software-only work can proceed
while cells charge separately. Simultaneous USB plus an active charger connected
to the robot has **not** been qualified: charger identity, rail/backfeed isolation
and electrical safety are unknown. Do not flash/reset/test in that arrangement
or invent a wiring workaround. Establish the documented isolated maintenance
arrangement first; otherwise remain software-only. No new tools are required
merely to repeat established software tests.

## 2. Reserve ownership and capture the starting state

1. Read root `AGENTS.md`, applicable component guides,
   [hardware records](../hardware/README.md), `hardware.json` and `firmware.json`,
   [Hermes operations](hermes-robot.md), and this protocol. `active_deployment`
   identifies the last installed image; a new build is only a candidate.
2. Use a separate worktree/branch; report its path, base commit and changed files.
   Never stash, stage, delete, switch branches over or publish another session's
   unknown dirty work. Claim the affected files/contracts with other sessions.
3. Name one hardware operator and scope the maintenance window. Worktrees do not
   isolate UARTs, RF, camera, OBS, Hermes profiles or power. Other agents stay
   software-only. Coordinate normal shutdown/release with the existing device
   owner; do not kill an unrelated chat or blindly stop shared services.
4. Before any serial open, obtain fresh physical motor POWER-OFF confirmation and
   establish support/isolation appropriate to the installed application. Serial
   open/DTR/bootloader exit can reset either board; stock startup can move servos.
   A historical OFF report, charging status, BOOT reply or low ADC reading is not
   independent proof of actuator-power isolation. Do not infer zero torque.
5. Map each physical board to its current stable port and expected MCU. Both
   CH340 bridges have the same generic VID/PID: `/dev/ttyUSB0` vs `1` is not an
   identity. Record robot Mega2560/signature1e9801 vs handheld328P/1e950f,
   current application hashes, power/charger condition and backup provenance.
   Recheck changed cabling; do not redo established photographs or discovery.

## 3. Edit and validate without hardware

Add a failing regression for a behavioral defect, then make the smallest fix.
Keep fault latching, local TTLs/watchdog, calibration reads, output mapping and
STOP-before-ACK ordering intact. No raw GPIO/serial/reset model tool is added.

From repository root, existing firmware checks are:

```sh
firmware/freenove-guard/check-safety.sh
firmware/freenove-guard/test.sh
AVR_ROOT=<verified-extracted-toolchain> firmware/freenove-guard/build.sh --all --output-dir <private-build-A>
AVR_ROOT=<verified-extracted-toolchain> firmware/freenove-guard/build.sh --all --output-dir <private-build-B>
```

The angle-bracket paths are operator-selected placeholders, not runnable literals.
Build inputs/toolchain pins and offline prerequisites are in the
[firmware README](../../firmware/freenove-guard/README.md). Build twice into
distinct directories; compare SHA256 of Mega and handheld HEX/ELF. Do not download
new revisions, alter the installed app or reuse a stale artifact to get a pass.

For host adapter changes, from `services/embodiment-gateway/`:

```sh
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen basedpyright
uv lock --check
```

Use actual native-driver and PTY/stdio surfaces, including bad input, STOP,
expiry/cancellation and false-completion boundaries relevant to the change.
These are software evidence, not HIL, physical cutoff or powered acceptance.
Record unavailable LSP tools and substitute compiler/type-check results honestly.

## 4. Controlled wired application update

This section is a gated checklist, **not** an unconditional flash command.

1. Record the authorized boards, exact candidate source commit, tool versions,
   HEX/ELF hashes, allowed memory ranges, power state, operator and rollback plan
   **before** writing. Confirm the artifact excludes EEPROM and bootloader records.
2. Preserve the currently installed images privately, with permissions/hashes and
   independent verification against the devices. Retain the immutable original
   baselines too. Use the [readback procedure](robot-readback.md); its commands are
   preservation-only and do not authorize adding writes to that procedure.
3. The demonstrated application method is AVRDUDE7.1,115200 baud: Mega `wiring`
   with `m2560`, handheld `arduino` with `m328p`, `-D` and application-only HEX.
   Select the exact verified local binary/config/library paths and identified
   device port from current records. Do not add chip erase, forced signature,
   EEPROM, bootloader, fuse or lock writes. No calibration rewrite or blind
   mutation retries. Maintain unchanged boards if their artifact is unchanged.
4. Retain programming/verification exit codes. Compare each affected board's full
   EEPROM with its pre-write baseline. Confirm untouched boot-region bytes using
   the established verification method. An application upload pass is not proof
   of all memory contents or electrical safety.
5. After reset/startup wait, obtain a real CRC-validated robot STATUS through the
   intended bridge. Require boot-disarmed/notbusy/no fault before any separate
   action tier; verify read-only supply/capabilities without treating ADC as power
   proof. Never send BEGIN/ARM/EXEC automatically to celebrate a successful flash.
6. On mismatch, disconnect, ambiguous write or failed verification, stop the
   maintenance transaction, keep physical POWER OFF and report actual evidence.
   Deliberately restore only the known-good application using the previously
   demonstrated method when recovery prerequisites still hold; verify full flash
   and EEPROM against that baseline. Do not brute-force retries or erase more
   memory. Serial-bootloader restoration is demonstrated; ISP/fuse/lock recovery
   is not. If the bootloader is unavailable, report the blocker rather than improvise.

## 5. Reset and qualification after an update

Use [agent-owned USB reset recovery](hermes-robot.md#agent-owned-usb-reset-recovery)
when authorized and necessary. Agents handle DTR reset while safely tethered;
ask the user to find a button only if that recovery is unavailable or unsafe.
Never automatically clear emergency faults or retry movement through resets.

Motor-off HIL is a separate recorded tier: verify the relevant real ingress/ACK
routes, STOP, fault latching, rejected rearm and deadline behavior without actuator
power. An ACK proves protocol state, not measured rail cutoff. A cross-ingress
STOP fix needs each changed live ingress qualified before manual/Hermes handoff
is declared accepted. Coordinate ownership; concurrent clients are not a test plan.

Only after separate powered authorization: verify disarmed power-on stays still,
then staged ARM-only behavior, then one allowlisted action at a time with local
deadlines and the operator at POWER. Record actual visible completion and STOP
evidence; do not generalize bench acceptance to floor/autonomy or all joint health.
Turn POWER OFF at handoff and record whether the user actually confirmed it.

## 6. Mandatory execution record and publication

Every maintenance slice records this checklist in the same commit series:

- date/operator, worktree/branch and exact source revision;
- requested scope, authorization and actual physical/charger/ownership conditions;
- before/after installed hashes vs built-only candidate hashes;
- exact commands/tool versions, test inputs, expected vs observed results,
  exit status and relevant raw protocol events;
- red/green regression evidence; build reproducibility; EEPROM/boot preservation;
- private log/media paths and hashes, not raw secrets, images or full transcripts;
- checks **not performed**, failure/rollback evidence and recovery limitations;
- final controller/power/port ownership, queued work and next safe step.

Update `docs/hardware/{hardware,firmware}.json` with discoveries/candidates and
actual device changes. Append firmware history for updates/resets/configuration;
never replace `active_deployment` with an unflashed candidate. Add a dated test
record under `docs/operations/`, link it from `PLAN.md`, and keep root/component
guides discoverable. A build-only record must explicitly say **no device access**.
Stage explicit task-owned paths, commit/push to the owning remote, and verify the
published revision. Host config changes additionally follow Chezmoi/GitGov;
network changes first require the managed host network reference. Do not publish
unrelated dirty work or leave agent-authored production changes only on disk.

Example completed software-only record:
[STOP routing, 2026-10-18](robot-stop-ack-2026-10-18.md).
