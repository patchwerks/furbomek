---
created: 2026-11-20T13:01:00Z
branch: codex/production-wave-11
author: patchWERKS / Codex
status: active
---
# Production motion and effects: HOLD handoff

**Release: HOLD.** The default is stationary, fixed RGB with motion held.
This Task 18 record describes the candidate software and the remaining physical
qualification. It creates no release manifest, installs nothing and grants no
runtime authority. Agents own setup, validation and recovery; the owner is not
expected to run internal tools. The [motion release ledger](../hardware/motion-profiles/RELEASE.md)
and [roadmap](../../PLAN.md#93-phuket-motion-qualification-for-streaming) define
which evidence can change this state.

## Observed scope and limits

| Surface | Evidence scope | Release consequence |
|---|---|---|
| Robot and bridge | Historical installed Guard images and eight operator-present supported-bench actions in [firmware records](../hardware/firmware.json) | Preserve supported-bench limits; no calibrated locomotion or unattended release |
| Tabletop forward | One supervised Active plus two Forward phases, normal DISARM, short uncalibrated advance in the [table record](macos-table-walk-and-media-2026-11-20.md) | No distance, stopping envelope, repeatability or transition qualification |
| Observation | Logitech C930e video and image-space scoring; fresh unmarked view lacks decoded tags | No measured stage calibration or clearance; cropped feet/boundaries cannot qualify |
| Printable reference | [A4 sheet](../../tools/motion-lab/fixtures/tag-sheet-a4.svg), raster tag decoding and digital dimensions verified | Actual print size, mounting and physical calibration remain unmeasured |
| Motion catalog | Eight verbs × ten synthetic trials exercise the [scorer](../hardware/motion-profiles/TRIALS.md); [catalog](../hardware/motion-profiles/catalog-v1.json) has zero physical trials | No measured motion profile; cower/shake and transitions remain unavailable |
| Portable stage | Two independently projected/calibrated synthetic layouts reuse one forward candidate via [stage verification](../../tools/motion-lab/STAGES.md) | Replay only; no second physical stage or transferred permission |
| Link and stop | [Native/PTY and abstract replay checks](../../services/embodiment-gateway/GUARD_ACCEPTANCE.md) | Installed authenticated origin/integrity/session freshness and measured independent cutoff remain unverified |
| Studio | Typed preview, owner HTTP and actual fixture-browser controls; [live adapter contract](../../apps/production-studio/README.md#private-owner-http-seam-task-24) | Fixture applied receipts do not establish installed effects, provider sessions or hardware authority |
| Candidate coordinator | Task 14 non-live stdio MCP → private Unix socket → actual Godot ACK agrees with private owner HTTP state; 464 gateway tests and 41 focused transport/controller tests pass | Candidate software evidence only; installed Mac/Brodex acceptance remains HOLD |
| Installed Mac/Brodex boundary | Read-only preflight observed seven original MCP tools, idle dedicated OBS and no fresh Kinect source | Original tool discovery does not establish candidate production-tool deployment |
| Archived GPU rehearsal | Actual Godot mailbox graphics ACK, duplicate refusal, fixed-view restoration and preserved owner override; offline encoded frames decode successfully | Archived-input graphics evidence only; no integrated OBS recording or actual SFX/HUD program output |
| Performance | Offline [qualification runner](../../tools/stream-qualification/README.md) checks metric arithmetic and fault replay | No actual ≥30-minute representative run, 24-hour soak or physical fault qualification |

Task 16's private rehearsal used archived inputs through the actual GPU,
Python scheduler and Godot mailbox. Its offline encoded playback is 4.633 seconds
at 1920×1080/30, SHA-256
`e45cf87772e87913d45f5c7cd3f98fd91ab6cc2f9ba46b16aa074b0f96fa5eb8`.
The encoding uses variable-timestamp archived GPU frames; its 30 fps is not a
measured real-time rendering cadence. This is not an OBS program recording.
The integrated OBS recording path was not established; actual SFX/HUD program
output and Brodex candidate deployment remain unproven. Task 16 restored the
dedicated OBS profile and observed idle output. Neither the archived rehearsal
nor a future temporary private OBS test establishes persistent deployment,
a live liquidation, ≥30-minute performance, 24-hour operation or physical
qualification. Synthetic provider
events remain labelled synthetic; no trade is required or authorized.

Task 14 candidate `f12f4126a1025dff1976e6a4bfb03d06fe968221` has recorded
non-live integrated acceptance, source bindings and passing lint/format/types.
The real fixture transports and Godot receipts establish candidate behavior;
they do not establish installed Mac/Brodex deployment, actual provider enrollment,
camera/audio acceptance or a physical permit. The execution owner's final
independent review remains pending at this snapshot.

The inspected documentation/qualification source baseline is
`843d4e13cf925c48910eb426991931d5d71eadf2`; it is not an installed runtime claim.
Task 17's actual offline CLI checks at that revision retain HOLD, with no actual
30-minute rehearsal, 24-hour soak or instrumented physical fault acceptance.

## Private state and source identity

Use the aliases `P` for the execution owner's private evidence root and `E` for
the private task receipts. Resolve them locally; never commit raw paths,
credentials, serial identities, recordings or host inventories. `E/18` holds
this handoff's command receipts; `E/14`, `E/16` and `E/17` hold the independently
reviewed integration, rehearsal and qualification dispositions. A missing or
incomplete receipt remains pending. These aliases are not shell variables set
by this document.

A future active stage would use `P/stages/active/release-qualification.json`.
No such release activation is performed here. Its exact source revision, robot
and bridge image hashes, profile, stage, calibration, motion-envelope identities,
session and evidence digests must agree with independently observed current
state. The historical image hashes in the ledger are comparison baselines,
not a new device read. Profile or image mismatch, stale session, missing cutoff,
wrong calibration, missing containment or unavailable observation must hold.

The current runner verifies only bounded candidate JSON and digest consistency.
It has no installed trust root, live instrumenter or physical permit issuer;
even internally consistent evidence envelopes cannot grant release. The current
[runner contract](../../tools/stream-qualification/README.md) explicitly leaves
that integration unimplemented. Do not turn a passing replay or supplied PASS
field into a release-mode manifest.

## Safe preparation and stage transfer

**Proposed procedure, not performed physical qualification.** Keep motion held
while preparing. Use existing gear first: installed robot/bridge, existing
external camera, a rigid reference board and chassis tag, measured containment
and an independent actuator cutoff. No automatic new MCU, radio, camera or stage
purchase follows. A larger surface or a new mount is optional and needs its own
measurement; this record assumes no stage dimensions.

1. Print the A4 sheet once at actual size/100%. Measure each black square at
   40 mm ±0.25 mm and adjacent reference centers at 120 mm ±0.25 mm. Record the
   measurement and print identity. Keep IDs 0–3 rigid and flat; cut only the
   lower ID 10 section and mount it rigidly on the chassis. Do not infer print
   dimensions from the PDF/SVG settings or ask for repeated power cycles.
2. Lock the camera so the full robot, every foot/contact region and the complete
   usable boundary are visible. A smaller fully visible region at the existing
   mount height is acceptable for investigation. A rear-only diagnostic view
   cannot prove clearance. Measure camera/target geometry, validate independent
   translations and yaw, and retain held-out error bounds under the
   [qualification rubric](../hardware/motion-profiles/QUALIFICATION.md).
3. Independently survey the stage frame, usable convex polygon, obstacles,
   edges, containment, material/finish, slope and traction intervals. Camera
   calibration does not constitute a containment inspection. Measure the
   independent actuator cutoff and stop behavior on the exact installed route
   under separately authorized supported conditions. Establish authenticated
   origin, integrity and boot/session freshness before broader motion admission.
4. Select only measured profiles matching robot/image/gait, load, posture, power
   and surface. There are currently none. Size the usable area from measured
   swept footprint, stop excursion, inter-observation travel, uncertainty,
   calibration error, displacement and explicit margin. Every edge and obstacle
   must clear the resulting envelope; a larger tabletop alone is insufficient.
5. When relocating the camera, invalidate the local calibration. When changing
   stage geometry or obstacles, invalidate the survey/containment. Preserve the
   historical robot-relative profile and its collection provenance, but recheck
   applicability. Changed surface/load/robot/gait requires affected-profile
   retesting. Never copy approval or calibration from the reference stage.
6. Only after the prerequisites pass, the designated operator may perform the
   separately authorized targeted translation/turn/stop and transition checks.
   Recheck exact identities and freshness at each step. New-stage release needs
   its own physical evidence and the execution owner's separate applicable
   approval. Offline `REPLAY_ELIGIBLE` never activates it.

## UI and MCP boundaries

The owner studio distinguishes fixture, unavailable and live modes. The typed
owner API accepts authenticated session/status/action requests, exact Origin,
CSRF and matching epoch/revision; unsupported controls remain unavailable with
reasons. Preview/save can remain useful under HOLD. Apply/revert/manual dispatch
require fresh controller authority and actual applied receipts. Owner override
must survive expiry; reconnect must mark historical state and re-observe it.
An injected fixture controller proves this seam only.

The existing Hermes profile is `furbomek`; its default-profile robot access stays
disabled. Existing bounded bench tools remain governed by
[Hermes robot operations](hermes-robot.md). Candidate production discovery and
semantic preview/cue acceptance require their own Task 14/16 receipts; do not
infer their installation from seven legacy tools. Hermes never gets arbitrary
serial, shell, GPIO or OBS access. Audience/provider data cannot bypass stage
admission. Unqualified movement must be omitted with a reason while an otherwise
admitted media-only cue can run; voice/head slots remain reserved.

## Executable non-live checks

Run from the repository root. These commands have no release authority:

```sh
python3 tools/stream-qualification/run.py --suite replay
python3 tools/stream-qualification/run.py --suite release-check \
  --manifest tools/stream-qualification/fixtures/representative.json
```

Replay success is exit 0 with `release: HOLD`. Release-check is exit 2 with
`physical_authorization: false` and `operational_io: false`. With a future
private candidate, an agent may substitute the explicit private manifest path;
that remains a local diagnostic. `approved-live` currently refuses before
opening any supplied manifest. No live launch command is supplied here.

Task 18 also repeats release-check with a consistent synthetic candidate,
missing authenticated-link evidence, different image, missing cutoff and wrong
calibration. Each must return exit 2/HOLD, with the corresponding diagnostic.
The synthetic candidate's successful consistency check is not an acceptance
success for physical release. The [media gate](../../tools/verify-media.sh) is
separate non-live verification and must run on the final composed source with
the configured Godot binary; it does not qualify OBS timing or hardware.

## Rollback and recovery

Keep the previous stationary workflow as the default. Cancel only the candidate's
owned cues and subscriptions through the typed owning controller; stop accepting
new candidate events. Restore fixed RGB or the incident scene only while that
controller still owns the affected property/revision. Do not overwrite an owner
manual change. Verify observed/applied receipts and actual idle recording/stream
status through the existing typed media surface. Close temporary owner sessions,
fixture browser/server and rehearsal processes; retain private evidence, and
restore only the exact owned temporary settings from their captured baseline.

If motion is active or uncertain, unconditional local STOP and the independent
actuator power cut take priority. Do not retry an ambiguous movement, automatically
clear faults, resume on reconnect or power-cycle to make status green. A fault
reset is separate maintenance requiring fresh confirmed POWER OFF under
[the robot runbook](hermes-robot.md) and [wired-maintenance rules](robot-wired-maintenance.md).
Returning to the historical supported bench requires its original support,
operator and cutoff conditions; it is not permission for table/floor travel.
Do not flash the historical image as an incidental software rollback.

This documentation handoff changes no host profile, firmware, calibration,
release configuration, public stream or provider account. Rollback of these
records alone has no runtime effect. Task 18's physical release/transfer
acceptance remains HOLD until the missing real evidence exists.
