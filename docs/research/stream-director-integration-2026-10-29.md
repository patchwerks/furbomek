---
created: 2026-10-29T16:46:46Z
branch: work/7-stream-director-prep
author: Codex
status: active
---
# Stream Director integration preparation

Canonical work: [speech integration #7](https://github.com/patchwerks/furbomek/issues/7).
This document prepares a bounded implementation; it does not satisfy that issue's
real Hermes, speech, recording or timing acceptance. [PLAN](../../PLAN.md)
sections 4.2–4.4 and 9.1 remain architecture authority, and GitHub issues remain
the task and dependency authority. Do not create a separate dispatch queue here.

## Inspected baseline

**Observed, source inspection:** Furb-o-Mek base
`9347304e866ca90e8eec2d85f3bd3c41002d9a42`. No live service, device, voice profile,
audio sink, camera or OBS session was accessed for this preparation.

| Existing seam | What is implemented | Integration consequence |
| --- | --- | --- |
| [Activity model](../../services/hermes-activity/activity_models.py), [reducer](../../services/hermes-activity/reducer.py) and [publisher](../../services/hermes-activity/publisher.py) | A bounded `agent.activity` projection with sequence, UTC publication timestamp, TTL and redacted timeline | Preserve the shipped projection; its timestamp is not an audio presentation clock. A tool completion or `turn_done` does not establish audible speech. |
| [Godot parser](../../tools/kinect2/godot/activity_event_contract.gd) | Accepts the reduced activity kind, sources, public audience/sensitivity and bounded payload | It is not a complete speech or cancellation consumer. Do not merely insert speech fields and claim the current renderer consumes them. |
| [Supervisor defaults](../../services/stream-supervisor/furbomek_stream_supervisor/defaults.py) and [ownership fence](../../services/stream-supervisor/furbomek_stream_supervisor/ownership.py) | One managed capture/tracker/activity/viewer/OBS process set; existing OBS configuration and recording cleanup | Extend this ownership boundary when a worker is qualified. A Director must not launch a parallel media stack or use stale persisted process IDs to stop another session. |
| [Readiness](../../services/stream-supervisor/furbomek_stream_supervisor/readiness.py) and [session lifecycle](../../services/stream-supervisor/furbomek_stream_supervisor/session.py) | Current-launch producer freshness, worker liveness, bounded crash restart and clean viewer/OBS exit handling | Media READY is not speech readiness. Preserve clean viewer/OBS exit as a session stop; avatar failover must not reopen an operator-closed viewer. |
| [Public speech adoption decision](voice-and-speech.md) and [PLAN §4.4](../../PLAN.md#44-canonical-speech-and-audio-plane-jabberwerk) | jabberWERK is the speech plane; the evaluated development baseline is a batch integration candidate | Consume qualified logical capabilities/profile IDs. Neither an engine's health response nor a generated audio file proves the full path. |

## Dependency order and ownership

The issue graph already separates independently reviewable work:

1. [#2 character broker](https://github.com/patchwerks/furbomek/issues/2) owns
   authenticated/local-authorized producers, ordered state, cancellation and
   reconnect snapshots, with a real read-only visible consumer.
2. [#6 Hermes lifecycle](https://github.com/patchwerks/furbomek/issues/6) consumes
   the accepted #2 interface. Hermes remains the sole planner and tool authority.
3. [#3 batch speech](https://github.com/patchwerks/furbomek/issues/3) qualifies the
   jabberWERK provider independently; [#5 fallback](https://github.com/patchwerks/furbomek/issues/5)
   qualifies the licensed static presentation independently.
4. #7 joins accepted #3, #5 and #6 evidence. Integration code should bind to their
   reviewed exact revisions, rather than implementing duplicate foundations.
5. [#8 recovery](https://github.com/patchwerks/furbomek/issues/8) qualifies the
   final integrated revision in its private soak. Earlier media-only evidence
   does not satisfy it.

The links describe required dependencies, not a cached status or a grant to run
live tests. Re-read issue comments, native dependencies and claims before each
implementation slice. The [tracker policy](../agents/issue-tracker.md) governs
claims and handoff. [#4 verification](https://github.com/patchwerks/furbomek/issues/4)
can develop offline checks independently. Physical #9/#10 gates remain separate.

## Proposed implementation slices after the foundation gates

The following division narrows #7 without adding new authorities or promising
unimplemented commands. Future file locations are proposals from PLAN, not
existing runnable interfaces.

| Slice | Owning boundary | Reviewable outcome before proceeding |
| --- | --- | --- |
| Batch result admission | Thin `integrations/jabberwerk/` client; engine/profile decisions stay upstream | Verify exact qualified capability and accepted artifact metadata; reject unavailable capability, invalid format, expired/cancelled session and unapproved fallback. Keep raw audio, profiles and authentication private. |
| Shared audio timeline | jabberWERK audio/timeline producer with the existing project broker as consumer | Document the actual qualified PCM format, clock origin, session/utterance/cancellation identities and sink position mapping. If the producer cannot provide the required contract, stop and resolve #3; do not fabricate a Director clock. |
| Read-only presentation | Existing project-owned broker and a qualified consumer from #2/#5 | Project speech start/end, mouth energy or genuinely available visemes onto the same timeline; retain redaction and snapshot/delta semantics. Renderer receives neither synthesis nor broker-write authority. |
| OBS sink and scene adapter | `services/stream-director/` under the existing media ownership boundary | Use allowlisted scene/sink operations with authenticated OBS access held outside renderers. Only the session owner manages processes; this adapter cannot start a public stream, mutate arbitrary OBS settings or control a robot. |
| Evidence and recovery | #7 timing evidence, then #8 final-revision qualification | Verify accepted audio reaches the intended private program and matches visible presentation; test independent failures and record the limits. |

## One PCM and cancellation timeline

These are acceptance requirements from PLAN, not a new wire schema:

- Keep session and utterance identity from the accepted producer through the
  broker, OBS sink and avatar. A new session must not inherit a prior session's
  pending utterance. Define the mapping in the reviewed producer/consumer contract.
- Compute speech/mouth presentation from the qualified PCM timeline. Wall-clock
  publication time, model tokens, process uptime and network arrival time are not
  substitutes. Any resampling or sink buffering needs an explicit position
  mapping to the same source timeline, with measured offset and drift limits.
- Cancellation invalidates queued output and transient presentation for the
  addressed utterance. Duplicate cancellation/end is idempotent. Late audio or
  animation must not revive a cancelled utterance, including after reconnect.
- Reconnect begins from the broker's current snapshot and resumes ordered fresh
  deltas. A sequence reset needs an explicit new generation/session; do not replay
  an old buffer to conceal an interruption. Bound every queue and retry window.
- Report generation cancellation separately from playback cancellation. A batch
  provider can finish computation after its output has been invalidated; this
  does not justify playing that result or claiming real-time barge-in support.
- Keep robot STOP independent of this pipeline. No audio, renderer, Director or
  network failure may acquire a robot route or weaken robot-local safety.

## Acceptance matrix

**Proposed; not executed by this preparation.** Deterministic tests must exercise
the accepted implementations and actual adapters, not a second idealized model.

| Case | Offline evidence required before private qualification | Additional acceptance evidence |
| --- | --- | --- |
| Command boundary | Unauthorized producers, unknown scene/capability and arbitrary action payloads fail closed; renderers cannot call privileged adapters | Inspect exact configured identities and allowlists during separately authorized private acceptance |
| Ordering and latency | Boundary cases for duplicate/out-of-order events, TTL expiry, bounded queue and future timestamps using a controlled clock | Measure event-to-visible latency and audio/video skew with method, clock mapping, sample count and uncertainty; fixture speed is not a measured media latency |
| Cancellation | Cancel before output, during queued output and after end; late result, duplicate cancel and stale handle cannot emit audio or transient animation | Measure request-to-last-output and request-to-visible-stop independently on the accepted sink |
| Network interruption | Disconnect before acknowledgement, after partial delivery and during cancellation; retry is bounded and cannot replay already consumed output | Verify the private sink's actual disconnection/reconnection behavior without substituting another voice or network route |
| Broker/Hermes failure | Stale state expires; snapshot recovery converges; no invented activity, duplicate speech or competing planner | Independent component stop/restart on the final integrated revision |
| Avatar failure | Static fallback policy preserves current session ownership and audio; no restart after intentional viewer/OBS close | #8 measures fallback within its two-minute criterion and completes its thirty-minute private soak |
| Recording and cleanup | Existing owned-process cleanup, recording finalization and ownership-fence regressions remain passing | Fully decode and inspect the final recording; a recording request or process-active flag is insufficient |

## Verification and handoff

This change contains documentation only. Validation is relative-link existence,
diff whitespace checking and a public-content scan; it supplies no new runtime,
audio, latency or recovery test result. The existing
[media verification entrypoint](../../tools/verify-media.sh) remains unchanged.
Its locked Python and real Godot consumer gates must pass for later implementation
changes, with missing prerequisites named instead of silently skipped.

Before #7 can be accepted, its reviewer needs accepted foundation revisions;
the real safe Hermes-to-jabberWERK-to-private-OBS path; measured timing and
cancellation; content-verified audio; reversible routing; and a sanitized dated
record. Independent review binds to the candidate commit. Reference #7 in this
preparation PR without a closing keyword: documentation cannot close the full
integration issue. No merge, deployment, live service activation, hardware access
or public stream is authorized by this document.
