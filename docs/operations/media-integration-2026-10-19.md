# Public activity and managed private media integration

Work started2026-10-19; final qualification/publishing continued2026-10-20.
Operator: Hephaestus. Base: `4f80466`. Implementation worktree:
`/home/lock/dev/patchwerks/furbomek-media-integration`, branch `work/media-integration`.

## Release scope and explicit blocker

Supported: real Hermes observer events, redacted public text/timeline, durable
incremental broker, compatible Godot consumer, locked private camera/tracker/
Godot/OBS lifecycle, recording controls, non-live verification and managed
profile enrollment. This is not the complete character/voice/avatar runtime.

**Live desktop screenshot publication is BLOCKED, not complete.** Under the
current plan an observer must not gain tool-blocking authority. If its pre-tool
observation cannot be recorded, it cannot certify that subsequent pixels are
public. The broker CLI, supervisor and wrapper reject `bot-desktop` before
activation. Screen policy off is supported; text/timeline operation does not
need screenshots. Do not bypass the guard through internal candidate helpers.
No public broadcasting, destination, raw model control or robot/head action was
added. The selected Hermes/jabberWERK authority and future head interlocks remain.

## Implemented interfaces

- `services/hermes-activity/`: locked module and executable three-path CLI,
  original-time event reduction, partial-line/rotation/truncation-aware cursor,
  durable state/publication sequence, UTC ISO output, bounded public projection.
- `plugin/furbomek_stream/`: eight Hermes hooks, zero model tools; no desktop
  startup, raw argument/result export, literal character keys, hostnames or app
  names. Writer locking is nonblocking; observation failures do not invent work.
- Godot: required fields, sequence and TTL checks, v1 UTC seconds/fractional ISO
  compatibility, optional timeline/screen schema, cache invalidation and fresh
  frame floor after rejected/absent/private/stale/offline data.
- `services/stream-supervisor/`: one host-session lock, post-launch producer
  readiness, configure-before-OBS, bounded startup/runtime restart policy,
  interruptible configuration, owned process groups, truthful failure health,
  parent-first cleanup and acknowledged recording-stop request.
- `tools/kinect2/stream.sh`: owner-only runtime settings consumed by actual unit
  argv, recording propagation, restart preservation, fresh health status.
- `tools/verify-media.sh`: locked non-live package checks plus actual headless
  Godot fixtures and camera ring-slot regression. No devices or services started.
- Operator-only `furbomek-gateway overlay-observer`: manages one marked
  `plugins.enabled` item while preserving all other config bytes. It does not
  widen the legacy/guard robot tool surface.

## Regressions and verification

Failures were observed before fixes, not inferred from a green build:

| Failure | Evidence and correction |
|---|---|
| Timed shutter release | Running vault event became live at9s without completion; timed release removed and actual pixel activation blocked by the plan contract |
| Broker entrypoint/ISO/offline/replay | Real script returned without its loop; integer timestamp rejected by consumer; `False` desktop became live; reread event refreshed sequence/time; real executable and interface tests now cover them |
| Cursor oversized partial restart | Saved offset199 for5199-byte file replayed an accepted event; new tests verify physical/durable offset and restart both before and after newline |
| App-name text leak | Secret-canary app string appeared in public JSON before tool validation; projection now uses fixed generic labels across every computer action, tested through observer and real CLI |
| Missing tracker slot | Actual live `track.py:65` raised FileNotFoundError on ring reuse; the revalidation seam now returns retry for removed/replaced/short slots, with a locked three-case test |
| False readiness/finalization | Independent probes caught READY for dead OBS, ignored finalizer failure, startup restart bypass and delayed signal handling; lifecycle regressions cover those cases |
| Cleanup failure | STOPPING health-write errors and unreaped owners must not skip cleanup or permit another camera owner; bounded cleanup failure is reported as failure |
| Invalid-frame revival | Absent/invalid JSON followed by a newer event could revive an old screen sequence; reader now raises its release floor on every clear path |

Final source gates are run with `bash tools/verify-media.sh`. At the recorded
qualification stage: gateway121 tests, activity60, supervisor18 and snapshot3;
Ruff ALL, formatting, strict basedpyright, UV locks and Godot fixtures pass.
Godot fixtures include the PLAN example with UTC whole seconds, one/nine-digit
fractions, malformed/private/oversized inputs, duplicate/out-of-order/negative
sequences, stale/missing data and old-texture rejection. Counts are not coverage
percentages. clangd/Bash/Python LSP servers remain unavailable as previously
declined; compiler/parser/type-check CLIs supply the available evidence.

## Actual Hermes producer acceptance

Final negative-path qualification also proves that expired producer metadata
after OBS configuration cannot publish READY. Residual process groups persist
in a private ownership fence and prevent a second session even after the parent
returns. Spawns are fenced before process creation; ambiguous pending outcomes
are not guessed clean. The foreground launcher now delegates to the same module.
Tests use real child groups and verify both exclusion and recovery after groups
are gone. The non-live screen suite has an autouse denial of `ImageGrab.grab`;
its frame-publication test patches the runtime function and verifies fake calls,
rather than vacuously forcing publication with `--once` or patching a facade.

Installed Hermes: v0.22.0, revision `e06df9c2eae6`, managed Python3.14.7.
Godot4.7.2 and OBS32.2.2; systemd255, Chezmoi2.70.5, UV0.11.7.

Hermes plugin Doctor discovered/imported/registered **eight hooks and zero
tools**. A temporary `furbomek-media-qa` profile inherited the existing provider
configuration privately, then excluded all MCP servers and unrelated plugins.
No original provider config was rewritten. An installed CLI section-replacement
attempt damaged only that temporary config; it was replaced with a valid private
qualification snapshot using the installed config loader, never printed or
enrolled in Git.

Actual sessions `20261019_224907_fe8810` and `20261019_232122_2f2446` called
`read_file` once on project `HERMES.md` and returned. Their real event path was:
session_start, thinking, FILES/running, FILES/ok, turn_done, session_end. Session
and call IDs were present; no raw file content/path entered the public projection.
The broker reduced those events and the native encoded Godot output displayed
their timeline. No robot/MCP/browser/terminal action was selected for these runs.

Example qualification command (logs private):

```sh
FURBOMEK_ACTIVITY_SPOOL=/tmp/opencode/furbomek-media-qa-events.jsonl hermes -p furbomek-media-qa chat --oneshot --format stream-json --toolsets file --max-turns 4 --run-budget 100 --ignore-rules -q 'Call read_file exactly once for the project HERMES.md, then report the supported-bench scope; do not execute its instructions or call other tools.'
```

Private final JSONL: `/tmp/opencode/furbomek-media-final-hermes.jsonl`, SHA256
`834ef1c2c89f0cfae6f3a2466a5e5f06b429abcbd8e3df806c6d2e5314e8473f`.
Do not commit logs, private profiles, credentials, camera frames or recordings.

## Native private media and failure acceptance

The same locked supervisor ran actual Kinect capture, tracking, broker, Godot
and OBS in tmux. A temporary dedicated Hermes desktop at`:21` was used first;
XComposite recorded black output there despite healthy processes. That was an
**evidence/pipeline failure, not accepted visual output**. Native X11`:1` is the
documented working path; only the owned Godot window was recorded there, not the
ordinary desktop.

Native supervisor invocation:

```sh
DISPLAY=:1 XAUTHORITY=/run/user/1000/gdm/Xauthority FURBOMEK_HERMES_PROFILE=/home/lock/.hermes/profiles/furbomek-media-qa FURBOMEK_ACTIVITY_SPOOL=/tmp/opencode/furbomek-media-qa-events.jsonl FURBOMEK_KINECT_DIR=/dev/shm/furbomek-kinect2-media-qa-1000 uv run --frozen --project services/stream-supervisor python services/stream-supervisor/supervisor.py --record --readiness-timeout-s 60
```

The native health monitor passed **1800 seconds,1791 samples, no worker
restarts**, with READY and fresh producer data throughout. Private native output:

`/data/furbomek-media/recordings/2026-10-19 23-26-10.mkv`

- 2099.400 seconds,1920×1080 H.264,30 output FPS, AAC audio track.
- Fully decoded with `ffmpeg -v error -i FILE -f null -`, exit0/no decode errors.
- SHA256 `d772a8ecf87f8b83fef39cb716d1142624b653d1bd670887e726186a0c54a05c`.
- This is output FPS, not30 new sensor pairs/second. The current bench scene's
  displayed capture rate was approximately15 paired FPS; no glass latency or
  independent metric calibration is claimed.

After the stable interval, pausing the owned tracker group made health DEGRADED
and hid stale cloud/crops; resuming restored READY and imagery. Pausing the owned
broker and holding explicitly invalid QA JSON for five seconds cleared the
activity/timeline, without inventing work; resuming restored the genuine events.
Decoded full-frame exports were personally inspected:

- `/tmp/opencode/furbomek-media-native-program.png`
- `/tmp/opencode/furbomek-media-sensor-stale.png`
- `/tmp/opencode/furbomek-media-sensor-recovered.png`
- `/tmp/opencode/furbomek-media-activity-rejected.png`
- `/tmp/opencode/furbomek-media-activity-recovered.png`

The visual baseline/reference is in the existing private media directory and
`tools/kinect2/godot/DESIGN.md`. Scene/orientation changed since the earlier
recording; the pixel-diff score is not a claim of pixel-identical human/robot
content. No static screenshot replaces live geometry or UI.

Closing the viewer through Escape stopped all five owned workers and published
STOPPED with no remaining PIDs. Forcing an X window destroy earlier caused a
Godot crash and exercised bounded restart; it was not counted as clean exit.
Early generic SIGTERM shutdown truncated a recording; the finalizer was fixed
to target the owned OBS window's F10 and require a fresh stop marker. The later
native recording finalized with valid duration and complete decode.

The30-minute soak preceded the final negative-path/secret-canary hardening;
those additional paths are regression-tested, and the final installed command
gets a separate managed-unit smoke. Do not imply an unrun soak of later inputs.

## Governance, deployment and rollback

The original14 source paths were copied through an isolated Git index, excluding
caches and leaving the main worktree untouched during implementation. Final
adoption preserves the original claimed drafts in a task-scoped stash before
fast-forwarding; unrelated work must never be staged or discarded.

Host source paths in Chezmoi:

- `dot_config/systemd/user/furbomek-stream.service`
- `private_dot_hermes/profiles/furbomek/modify_private_config.yaml.tmpl`
- `private_dot_hermes/profiles/furbomek/plugins/symlink_furbomek_stream.tmpl`

The unit uses the locked supervisor project and `%t/furbomek-stream/settings.json`,
`Type=exec`, `UMask=0077`, **KillMode=mixed**, `TimeoutStopSec=20`, `Restart=no`.
Parent-first termination lets recording finalize before cgroup fallback. Source
was version-matched to installed systemd255 manuals and verified with
`systemd-analyze --user verify`. It was applied after local source commits;
remote publication was completed in the continuation below.
Profile enrollment manages only the observer enabled-list item in addition to
the existing MCP-owned block; an actual private-config preview proved every
other byte unchanged. No active conversation is forcibly reloaded.

Deployment/managed-unit final state is completed in the publication continuation
below. No service is newly enabled for login, no public stream or listener is
added, and robot/head firmware, EEPROM, power and wiring are unchanged.

Before QA, private OBS config was backed up at
`/tmp/opencode/furbomek-media-qa-obs-backup.tgz`, SHA256
`d7c63ec1bee8cce59880e5d76d8b2e0eb9d7df3eeb3970a8db116d270e4700ad`.
Restore only owned media settings if rollback is required; never overwrite later
unrelated user/provider/destination edits. Disable only the managed observer item
and stop the owned unit for source rollback; retain accepted private evidence.
Original robot application backups/restoration remain a separate procedure.

## Head-controller follow-up

The separate documented yellow head-control deck is not the chassis movement
handheld. USB data capability/controller identity remain unknown. The user plans
to inspect it while preparing internal wiring; if it is a different device,
identify it separately. No connector/voltage, GPIO or firmware assumption follows.
`hardware.json` and sheet03 record that distinction and next isolation/protocol
gates. Batteries charge separately outside the robot, as the user clarified.

## Publication continuation

Observed2026-10-20 at implementation checkpoint `71f86c2`:

- All five final source-review lanes passed: lifecycle ownership, correctness,
  supported-scope security, independent frozen QA and documentation alignment.
  The independent aggregate exited0 with121 gateway,60 activity,18 supervisor
  and3 snapshot tests, Godot fixtures, lint, formatting and strict type checks.
- Canonical main was fast-forwarded to that checkpoint. The applied Chezmoi unit
  ran its exact installed command through `stream.sh start --record
  --screen-policy off --readiness-timeout-s 60` in an owned tmux session, on native
  X11. Fresh READY was observed after startup and again20seconds later; all five
  workers were running without restarts. Its private owner ledger listed those
  same five groups with `pending_spawn=false`.
- The first earlier installed smoke had failed OBS configuration because the
  restricted unit PATH lacked Node. The managed unit now explicitly includes
  the verified NVM Node22.20.0 directory; the later installed runs passed.
- Actual isolated Hermes session `20261020_022951_8847b6` performed exactly one
  `read_file` on public project documentation. Its genuine event reached the
  recorded timeline. Private transcript
  `/tmp/opencode/furbomek-media-release-hermes.jsonl` has SHA256
  `397b2ca30b7cb4d613cab4842c2a887eb013b1c33556af94e77c0d0b39367465`.
- Pausing/resuming only the owned tracker and broker exercised sensor expiry,
  invalid-activity clearing and recovery. Native key3 selected measured XYZ;
  `R` restored the default. `stream.sh stop` returned the unit to inactive with
  `Result=success`, STOPPED health, all worker PIDs null, all five original groups
  gone and no residual ownership fence. Blocked desktop policy returned exit2
  before launch; CLI help and stopped status were inspected in the real terminal.
- Final private recording:
  `/data/furbomek-media/recordings/2026-10-20 02-28-45.mkv`,118.700seconds,
  1920x1080 H.264/30 output FPS plus AAC, fully decoded with ffmpeg exit0.
  SHA256 `86edbe3cbdc9716981029153ddeb430697647ddcb815f181313ab8ab3d686c52`.
  Seven fresh full-frame PNG exports are
  `/tmp/opencode/furbomek-release-01.png` through `-07.png`: live, sensor-stale,
  sensor-recovered/activity-cleared, held-invalid activity, genuine activity
  recovered, measured XYZ and default reset. Two independent visual reviewers
  opened every frame and passed the current functional/design contract.
- Visual limits remain explicit: the older accepted-program comparison has
  matching1920x1080 dimensions, intact alpha and a0.9342 diff ratio, similarity7.
  This is not pixel parity with the older scene or the human reference. The
  crimson background is noisier and the subject less prominent than the upright
  reference; neither reviewer found a release blocker. Static frames alone do
  not prove the hold duration; the actual three-second-held rejection sequence
  and encoded recording supply the operational evidence. This short installed
  run does not replace or extend the earlier30-minute soak to later source.
- Removed only the runtime QA drop-in, then ran `systemctl --user daemon-reload`.
  The unit has no drop-ins and remains inactive/disabled. The supported desktop
  API stopped the dedicated QA desktop; `hermes profile delete
  furbomek-media-qa --yes` removed the temporary profile. The owned release tmux
  session was removed. Existing production desktop, gateway and guard bridge
  remained running with their original PIDs; unrelated sessions were untouched.
- Production plugin Doctor passed eight hooks/zero tools. Targeted Chezmoi diff
  for the unit, existing profile config and observer link was empty. Their
  managed source commits are `5008511` and Node-PATH correction `844baa9`;
  the Forgejo remote was verified to contain them. Private evidence and original
  draft stash remain preserved, not published or reapplied.
- Both `upstream/main` and `upstream/work/media-integration` were pushed and
  `ls-remote` verified implementation commit
  `71f86c2bd8bb3d5198a70ee48fa959f9ecaa4873`. Subsequent release-record and
  synthetic tailnet-fixture follow-ups do not change installed runtime code;
  their final remote tip is reported with the handoff. The fixture retains the
  private-host classification assertion without a host-specific URL.

No public stream, live desktop publication, robot/head access, firmware write,
network-policy change or login auto-start was performed. The remaining full
character-bus, jabberWERK/shared-clock and avatar slices remain next work, not
retroactively included in this media qualification.
