---
created: 2026-11-20T13:01:00Z
branch: codex/production-wave-11
author: patchWERKS / Codex
status: active
---
# Motion release ledger

**HOLD — no measured portable motion profile or qualified active stage.**
This ledger records the Task 18 handoff, not a release-mode configuration.
See the [operations record](../../operations/production-motion-and-effects.md)
for private aliases, stage transfer, camera relocation and rollback. A fresh
runtime must independently establish matching current identities and physical
PASS receipts; this document cannot issue them.

## Exact historical scope

| Item | Evidence status and applicable class |
|---|---|
| Robot | **Observed:** modified Freenove hexapod, V3.1 controller / ATmega2560 and handheld bridge; [hardware records](../hardware.json) retain method limits |
| Installed Guard baseline | **Measured historical installation:** `active_deployment` in [firmware records](../firmware.json); no new readback in this slice |
| Mega HEX SHA-256 | `09157b7dbe220843a6feb29dccc0fe85bfb963c9fcfd9b867af11b7abdc6acb6` |
| Bridge HEX SHA-256 | `0aada2dd6109adb096261fec9735610a49015cf3066818fde8d735e91250114a` |
| Candidate firmware | STOP ACK candidate is separately `pending_deployment`; its build is not the installed Mega identity |
| Supported behavior | **Observed historical:** eight bounded actions with operator present and chassis supported; normal DISARM and separately verified emergency STOP |
| Bare-table behavior | **Observed historical:** short two-phase forward advance; distance, physical stop envelope and repeatability unmeasured |
| Servo calibration | **Observed offline:** installed/candidate AVR decoding agreement; EEPROM unchanged, physical alignment quality not independently measured |
| Observation calibration | **Observed replay:** two synthetic camera poses; digital A4 tags verified. Fresh Logitech view has no measured mounted metric references |
| Surface classes | **TBD:** no measured portable material/finish/slope/traction class; supported bench and historical bare table are not qualified travel surfaces |
| Motion profiles | **Observed software:** [catalog](catalog-v1.json) has zero physical trials for all eight verbs and no measured profiles |
| Stage transfer | **Observed replay:** two synthetic layouts reuse one selected forward candidate; no second physical stage or physical translation/turn/stop acceptance |
| Authentication/cutoff | **TBD:** actual installed authenticated origin, integrity, session freshness and independent measured actuator cutoff |

Keep robot-relative profile identity distinct from collection-stage and camera
identity. A new stage can reuse a measured profile only if its robot/image/gait,
posture/load/power and surface conditions remain inside that profile's measured
envelope. Geometry, calibration, containment and obstacles require independent
new-stage evidence. See [qualification](QUALIFICATION.md), [whole-set trials](TRIALS.md)
and [stage verification](../../../tools/motion-lab/STAGES.md).

## Release requirements still open

- Physically measured print/mount, full feet/boundary visibility and independently
  validated metric pose with bounded error and freshness.
- Whole-set calibrated trials, measured stopping/interval excursion, surface
  ranges, transition qualification and independently inspected containment.
- Installed authenticated link and independent actuator cutoff/STOP receipts,
  tied to exact image/profile/session, including actual loss/reset/brownout cases.
- Actual representative 1920×1080/30 rehearsal for at least 30 minutes with ≤2%
  rendering lag, local cue p95 ≤250 ms and idle motion-dispatch p95 ≤500 ms;
  report provider/camera/encoder delay separately.
- Authorized private 24-hour soak with battery-service holds, fresh resumption
  prerequisites and real fault matrix, without unexpected actuation or stale resume.
- Independent review of integrated runtime, owner/MCP and encoded program
  outcomes, followed by separate applicable release approval. A temporary
  synthetic media rehearsal does not satisfy physical or duration gates.

The current [offline release checker](../../../tools/stream-qualification/README.md)
always holds release. It diagnoses supplied JSON only and cannot verify installed
state or execute the proposed live workflow. Missing authenticated-link/cutoff,
wrong image/calibration or stale receipts refuse; a self-attested complete set
also refuses. No manifest is activated by this ledger.

## Preserved fallback

Stationary fixed RGB remains the default. Media-only cues may run only through
an independently admitted, verified media path. Physical and reserved capabilities
stay unavailable. The historical supported bench is a separate, operator-present
scope, with its own current preflight; it never inherits portable-stage admission.
Normal success does not require reset. Emergency STOP/faults stay latched until
separately authorized recovery. No hardware, firmware or calibration changed in
this documentation slice; the existing records and private preservation remain
unchanged.
