# STOP acknowledgement regression and wired-maintenance handoff

Date: 2026-10-18. Operator: Hephaestus. Scope: **software only; no device access**.
Base: `b87f7e98559ae322d68669cc4dd65c68c9e427e5`.
Worktree: `/home/lock/dev/patchwerks/furbomek-stop-ack`;
branch: `work/stop-ack-maintenance`.

## Existing local work, not part of this slice

The original `/home/lock/dev/patchwerks/furbomek` checkout is on `main` at the base
above. It already contains four unstaged modifications:

- `tools/kinect2/godot/AGENTS.md`
- `tools/kinect2/godot/DESIGN.md`
- `tools/kinect2/godot/activity_ports.gd`
- `tools/kinect2/godot/broadcast_hud.gd`

It also has untracked `services/hermes-activity/`, `services/stream-supervisor/`,
`tools/kinect2/godot/activity_event_reader.gd` and `tools/kinect2/stream.sh`.
These concern activity projection/broker/feed, stream supervision and Godot HUD
integration. Their author/current owner has **not** been established. They were
not authored, staged, stashed, overwritten, deleted or published in this slice.
The separate `furbomek-brodex-bootstrap` worktree/branch also exists; this slice
does not claim ownership of it. This inventory is a dated local observation,
not a permanent assertion about future working trees.

## Defect, red/green proof and scope

Hypotheses: STOP fails to quiesce; quiescence succeeds but the previous owner
captures its ACK; or the RF envelope/source selects the wrong path. The native
regression uses the real dispatcher/frame/RF code and a motion sink/reply sink.
The sink requires safe-stop before each STOP ACK and checks Fault4/notbusy.

The final regression on the unchanged production dispatcher failed:

```text
$ firmware/freenove-guard/test.sh
guard source scan passed
Assertion `replies.received.back().route == requester' failed.
```

An earlier test assumption that raw USB emits exactly one total frame was invalid:
its parser can also emit an error reply. The regression counts STOP ACKs rather
than unrelated replies, then reproduced the actual wrong-destination failure.
No production code was changed to accommodate that fixture correction.

`Dispatcher::stop()` emits the synchronous Guard ACK before clearing ownership;
`Dispatcher::send()` therefore used the old owner's route. The minimal fix routes
STOP ACK opcode0x31 to the current ingress while retaining owner routing for other
owned-session replies. It does not clear ownership before quiescence, alter the
raw STOP primitive, reset Fault, renew leases or add a reset tool.

After the fix, `firmware/freenove-guard/test.sh` passed (exit0), including the full
previous native/driver suite and the new matrix: all nine USB/computer-RF/manual-RF
owner/requester pairs, each in Boot, Session, Arming, Armed, Disarmed and Fault,
plus Armed/busy (63 cases), repeated STOP and rejected rearm. A dedicated real
RF STOP envelope test also verifies a pending ARM ACK still reaches its manual
owner while the STOP ACK reaches computer ingress. All are host-simulated sinks,
not actual RF/HIL or electrical measurements.

Independent Oracle review found no correctness or maintenance-safety blocker.
Its test-precision observation was addressed by counting safe-stop invocations:
every STOP ACK, including duplicates, now requires a newer safe-stop count than
the previous ACK. The final native suite passed after that test-only tightening;
production AVR inputs and the reproducible firmware hashes were unchanged.

## Builds and manual surface check

From this worktree:

```sh
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain firmware/freenove-guard/build.sh --all --output-dir /tmp/opencode/furbomek-stop-ack-a
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain firmware/freenove-guard/build.sh --all --output-dir /tmp/opencode/furbomek-stop-ack-b
firmware/freenove-guard/test.sh
bash -n firmware/freenove-guard/build.sh
```

Both builds passed, including native tests and AVR policy/disassembly checks.
Matching SHA256 in both output directories:

| Artifact | SHA256 |
|---|---|
| Mega candidate HEX | `7961cd3ca7ec19cc1a8fb88ace49f69f3d300a0062e443a21a3762fc438581de` |
| Mega candidate ELF | `85d39d08e1280ab625ecff305915b5040e690c1fc8b233011111a1810a625674` |
| Handheld HEX, unchanged | `0aada2dd6109adb096261fec9735610a49015cf3066818fde8d735e91250114a` |

Compiler/tool pins are recorded by the build and firmware README: native GCC13.3,
AVR GCC7.3, pinned ArduinoCore1.8.6 and hash-checked vendor preimages. clangd and
Bash LSP are unavailable and installation was previously declined; strict compiler
checks and `bash -n` substituted. No new tool/config installation was performed.

Personally exercised the candidate native driver in tmux: `manual begin`,
`manual arm`, `stop`, rejected `manual arm`, and invalid input. Observed ordering:

```text
MOTION safe-stop
RADIO robot->RF_COMPUTER result=ACCEPTED state=FAULT busy=0
STATUS state=FAULT owner=0
RADIO robot->RF_MANUAL result=WRONG_STATE state=FAULT busy=0
ERR command
```

Startup help rendered; the native suite also exercises `--help`. The temporary
tmux session was removed. Test-script scratch builds are automatically removed;
candidate build directories remain outside Git. No instrumentation/core dump was
retained (`ulimit -c 0` during expected failing runs).

## Installation, rollback and next gate

**Not flashed.** Installed Mega HEX remains
`09157b7dbe220843a6feb29dccc0fe85bfb963c9fcfd9b867af11b7abdc6acb6`;
installed handheld HEX remains the value above. No serial port, reset, RF device,
camera, firmware/EEPROM write, power toggle, charging connection or live Hermes
session was used. The last physical checkpoint remains the earlier user-confirmed
POWER OFF / USB-reset / RF-verified BOOT; it was not remeasured here.

Source rollback is reverting this fix in Git, not a device restore. Original
private baselines and demonstrated application-only restoration are unchanged.
The installed image still has the ACK-routing defect. Before deployment, follow
[wired maintenance](robot-wired-maintenance.md): fresh power/isolation/ownership
confirmation, authorized Mega application update, preservation/verification and
motor-off cross-ingress HIL. No full manual/Hermes handoff, charger-connected USB,
powered candidate or unattended qualification is claimed. The 92-test host suite
and prior powered acceptance are previous evidence, not rerun live-device tests.
