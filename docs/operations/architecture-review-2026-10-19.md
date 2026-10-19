# Architecture and project state review

Date: 2026-10-19. Baseline: `8ed82f1`, plus the existing dirty stream/activity
source in the main checkout. Method: architecture-review skill, five scoped
source reviews, parent verification of findings, safe module-driver executions,
dependency audits and a build attempt. No runtime implementation was changed.

## Executive assessment

Furb-o-Mek is **several useful, partly qualified modules, not yet one integrated
autonomous streaming runtime**. The robot-control module is materially further
along in deterministic policy, tests and evidence than the character/media
integration. The legacy browser application is a separate prototype, not the
Hermes robot brain. The dirty stream work is relevant implementation of the next
integration slice, not a backlog that must wait for every robot gate to close.

The main structural issue is uneven interface verification: individual functions
can pass tests while the executable, producer/consumer or process-lifecycle
interface does not work. Finish those seams; do not begin a wholesale rewrite or
create all the proposed directories merely to make the tree resemble the plan.

## 1. What actually exists

```text
CURRENT ROBOT PATH, supported operator-present bench scope
Hermes furbomek profile
  -> stdio MCP / guarded host policy
  -> exclusive USB UART to handheld bridge
  -> RF -> Mega dispatcher / Guard -> retained vendor gait
                          -> AVR output cutoff and local deadlines

CURRENT MEDIA PATH, separately operated
Kinect -> native capture -> sequence-tagged ring files
       -> Python tracking -> matched Godot presentation -> isolated OBS

LEGACY APPLICATION, separate from those control paths
Nuxt/browser -> OpenAI Assistants + Deepgram + browser TTS adapters
            -> standalone Express provider-forwarding proxy

DIRTY INTEGRATION, incomplete
Hermes observer hooks -> JSONL spool -> activity broker -> activity.json -> Godot
candidate supervisor -> capture / tracker / broker / Godot / OBS

TARGET, not yet delivered end to end
Hermes -> character state + jabberWERK speech/timing
       -> avatar / stream direction / measured physical-face adapter
```

| Module | Actual state | Important exclusion |
|---|---|---|
| Guarded host MCP and robot firmware | Installed and actually exercised for eight bounded supported powered actions; normal DISARM and terminal STOP | Not floor travel, authenticated RF or unattended autonomy |
| STOP requester-ACK correction | Source fix, route/state regressions and reproducible candidate complete | Candidate is not installed; live cross-ingress HIL remains pending |
| Independent `firmware/robot-safety` | Native-tested actuator-disabled diagnostic | Not the installed motion firmware; do not substitute it for the guarded image |
| Kinect/tracking/Godot/OBS | Implemented host path with prior private recording and first-run acceptance evidence | This review did not requalify visual fidelity, devices, FPS or lifecycle soak |
| Dirty Hermes activity/supervision | Real prototype code and 21 unit-test cases; relevant to PLAN §9.1 | Broken integration interfaces; not a completed character broker or managed runtime |
| Legacy Nuxt/Express | Browser conversation/TTS prototype | No robot authority; browser-secret and lifecycle debt; current build unverified |
| Voice/avatar/head/platform automation | Architecture and staged plans, not an integrated local runtime | No completed jabberWERK-to-OBS/shared-clock/avatar/face or public-streaming proof |

The loaded `furbomek-stream.service` was observed **inactive** in this review.
Its host-private unit references the dirty supervisor. This is deployment wiring,
not proof that the prototype works. No service was started or stopped.

## 2. Findings, ordered by consequence

### High before enabling live screen output: privacy release is not fail-closed

`services/hermes-activity/broker.py:134` releases its shutter after eight seconds
based on time since an event, not sensitive-operation completion. A safe driver
created a running vault event and observed `shuttered` at1s, then `live` at9s
without any completion event. The existing test explicitly expects that release
(`tests/test_broker.py:38`). Text redaction alone also does not protect pixels:
`plugin/furbomek_stream/projection.py:122` redacts typing text but does not request
a shutter. Treat this as a blocker before public screen capture is activated,
not evidence that a currently active stream leaked a secret.

### High before treating the legacy app as production: credential and proxy policy

`app.vue:318` persists the complete settings object, including provider keys, to
localStorage; `src/chat/openai-assistant.ts:24` explicitly enables browser-side
credentials. `server/tts-proxy.js:8` enables broad CORS and has no caller
authentication. Its `listen(PORT)` at line118 does **not** specify loopback;
printing a localhost URL does not restrict binding. Actual reachability depends
on runtime and network policy, which this review did not test or change.

This is a source-level production-readiness problem, not proof of Internet
exposure or server-owned credential theft: the proxy forwards caller-supplied
credentials. Do not extend it with robot/OBS authority. The selected speech
direction remains jabberWERK, not a new parallel provider gateway.

### High for delivery: the dirty broker is not runnable through its launcher

`services/hermes-activity/broker.py:204` defines a loop but has no executable
entrypoint. The supervisor launches the file with positional arguments
(`services/stream-supervisor/supervisor.py:61`); safe script execution confirmed
that it returns without starting that loop. The caller's actual interface is
untested even though broker state functions pass tests.

### Medium-high: producer and consumer contracts disagree

- Broker `observedAt` is integer milliseconds (`broker.py:64`); the actual Godot
  reader requires an ISO8601 UTC string (`activity_event_reader.gd:101`).
- Production passes the boolean returned by `desktop_alive()` to `screen_state()`
  (`broker.py:216`); that function only recognizes `None` as offline
  (`broker.py:143`). A driver verified `False -> live`, while `None -> offline`.
  The existing offline test passes `None`, so it misses the production call shape.
- The loop rereads/reapplies the complete spool (`broker.py:213`,
  `hermes_feed.py:30`). Replaying the same event increased sequence1 to2 and
  refreshed its activity time in a driver. This can keep old activity apparently
  current and defeat idle/expiry intent.

These are concrete integration defects, not reasons to discard the work. Keep
the reader, producer and related Godot changes together while repairing them.

### Medium-high: media lifecycle is not owned end to end

The working launcher checks child liveness during startup, then waits on OBS
without monitoring every child (`tools/kinect2/launch-host.sh:44`, `:59`). Closing
Godot or losing tracking can leave the other processes alive. The dirty supervisor
aims at this gap, but lacks launcher parity for locking, readiness and OBS setup;
its restart count is not a real sliding window (`supervisor.py:174`). Its wrapper
accepts `--record` without transmitting the option (`tools/kinect2/stream.sh:11`).
Do not replace the existing launcher until fixture-process lifecycle tests and
private acceptance prove the replacement's interface.

### Medium: media snapshot failure handling has an untested race

Sequence-tagged snapshots and TTL rejection are good existing defenses.
`track.py:51` catches missing artifacts throughout `load_snapshot()`; the claim
that all ring rollover reads are uncaught would be incorrect. However, the later
frame-header reopen at `track.py:65` is outside that catch. Ring-slot reuse during
that reopen can raise an uncaught missing-file error. This is source-inspected,
not reproduced against the live camera. Add a deterministic fixture regression
before changing publication or reader behavior.

### Medium: legacy lifecycle/audio correctness has no regression safety net

`app.vue` is882 lines and owns settings, microphones, rendering, conversation,
STT, TTS and cancellation. The MediaRecorder callback registered at line720 is
not the same function removed at line815. Visualizer initialization creates new
AudioContexts/animation loops without a retained teardown. PlayHT discards its
first stream chunk as headers and carries only an offset, not a split PCM sample
(`src/tts/playht.ts:116`, `:169`). OpenAI thread/run failures lack an explicit
recovery event. These are source-inspected correctness risks; no live provider
or browser reproduction was performed. There is no source/server test suite to
lock these behaviors before a refactor.

## 3. Qualification gates are not the same as code bugs

The installed STOP routing issue affects who receives the ACK, not whether STOP
quiesces/latches. Its candidate already has native tests; deployment/HIL is the
remaining step. Preserve that distinction.

AVR Timer4 owns cutoff independently of the blocking gait loop, but the actual
electrical cutoff and watchdog-reset behavior remain unqualified. A main-only
stall is not necessarily detected by a watchdog fed from Timer4. Finite sequence
ordering is not authentication. Floor locomotion, battery-only/untethered use,
manual handoff, head electrical integration and unattended operation have separate
acceptance gates. Do not label the present supported-bench result a general
safety certification, or make all these gates prerequisites for offline stream work.

## 4. Structural integrity: strengths and debt

**Strong existing depth:** the pure Guard module hides protocol/state-machine
complexity behind motion/reply interfaces. The native AVR and host-test adapters
make those real seams. The host guarded module concentrates allowlists, sequence
handling, cancellation, bounded operations and STOP cleanup. Its92-test evidence
includes real PTY and MCP stdio interfaces, not only parser mocks. Deleting those
modules would spread safety policy into many callers; they earn their depth.

**Uneven locality elsewhere:** activity lifecycle facts are spread across plugin,
spool reader, broker, image publication, Godot and supervisor. Tests mostly cross
individual functions rather than the interfaces their callers actually use.
The legacy root module similarly owns too many lifecycles. More tiny files alone
will not improve either issue; concentrate ownership and test through the seam.

**Delivery/documentation debt:** there is no repository-wide CI, root verification
entrypoint or meaningful legacy test script. Camera/Godot have recorded runtime
evidence but no checked-in automated test suite. Domain decisions live in
`AGENTS.md`, `PLAN.md` and research notes; no `CONTEXT.md` or ADR directory exists.
The old one-shot document still says perception and embodiment firmware are not
implemented, although real implementations now exist under other names. This is
documentation drift, not a reason to rebuild those modules.

## 5. Validation and its limits

Fresh review observations:

| Check | Result |
|---|---|
| Safe broker privacy driver | Sensitive operation still running: shutter opens after8s |
| Safe broker replay driver | Same event increments sequence and refreshes activity time |
| Safe broker offline driver | Production `False` is published as `live`; test `None` is `offline` |
| Root `npm run build`, Node22.20.0 | Could not run: `nuxt: not found`; dependencies were not installed to mask this limitation |
| Root `npm audit --ignore-scripts --json`, npm10.9.3 |75 affected package entries:6 critical,51 high,13 moderate,5 low |
| Nested proxy audit |8 affected package entries:1 critical,3 high,1 moderate,3 low |
| Host stream unit | Loaded, inactive; no state changed |

Audit counts include direct/transitive and development dependencies. They are not
counts of proven remotely exploitable flaws and must not be added together as
deduplicated issues. Do not run force-upgrades as part of an architecture review.
Raw audit JSON is outside Git under `/tmp/opencode/furbomek-{root,proxy}-audit-2026-10-19.json`.
SHA256: root `e63078220178d131d95b5e622549a00415080f36d7795b1a2c21f98aef28ce0c`;
proxy `30c4da9471994af2a0e25e5670c263f70b224f7d1afa9684459fc44bc8937189`.

Existing evidence, not rerun or promoted in this review:92 guarded host tests,
21 dirty activity unit tests, native STOP route/state matrix, matching AVR builds,
supported powered Hermes acceptance and prior OBS recording. No robot, camera,
live Hermes, browser/provider, desktop capture, OBS or public stream was started.
No source defects were silently fixed. Dirty implementation files are unchanged.

## 6. Deepening candidates

1. **Public activity module: first priority for the dirty work.**
   - Files: activity plugin, `hermes_feed.py`, `broker.py`, Godot activity reader.
   - Problem: privacy, freshness, replay and publication are distributed; passing
     function tests do not prove the producer/consumer interface.
   - Solution: concentrate activity/privacy/frame lifecycle behind one coherent
     module, retaining the existing adapters rather than replacing the design.
   - Benefits: locality for release/expiry decisions; leverage from tests that
     exercise real plugin-spool-broker-consumer fixtures and the executable path.
   - Deletion test: removing this ownership would scatter the same policy back
     across every adapter; it is real depth, not an ornamental abstraction.
2. **Media session module.**
   - Files: launcher, dirty supervisor, wrapper and host unit source ownership.
   - Problem: startup, shutdown, restart, recording and health have competing owners.
   - Solution: give one module ownership of the complete private media session;
     make the launcher/service adapters cross the same tested seam.
   - Benefits: locality for cleanup and restart rules; fake-child tests provide
     leverage without requiring camera/OBS for every lifecycle regression.
   - Deletion test: child lifecycle policy would reappear in each launcher if the
     module vanished, so central ownership is justified.
3. **Matched snapshot module.**
   - Files: native publication, Python snapshot/tracking reader and Godot loader.
   - Problem: several rotating artifacts represent one logical frame; recovery
     knowledge is repeated across readers and an outside-catch reopen.
   - Solution: deepen the existing sequence/manifest seam and localize read/retry/
     expiry semantics; begin with fixtures, not a transport rewrite.
   - Benefits: locality for generation and race rules; leverage from reusable
     mismatch/partial/missing/stale fixtures across the two real reader adapters.
4. **Repository verification module.**
   - Files: package-specific checks, entrypoint docs and future CI definition.
   - Problem: there is no single trustworthy answer to what a checkout can verify.
   - Solution: one non-live verification interface delegates to the existing
     npm/UV/native checks and reports unavailable prerequisites separately.
   - Benefits: locality of evidence and greater leverage for every new session;
     does not pretend the proposed production bootstrap CLI already exists.

These are candidates, not approved new interface designs. Keep Hermes as the sole
planner, jabberWERK as the selected speech/timing plane, renderers unprivileged and
robot safety independent of media health. Do not introduce a second speech stack
or demand completion of the target directory layout before delivering a slice.

## 7. Work order without artificial dependencies

**Track A, start now:** finish the existing dirty public-activity module: privacy
release first, then real executable/producer-consumer/cursor fixtures, then media
session supervision, then a private Hermes-to-Godot/OBS acceptance run. Commit
only the coherent tested source, excluding generated caches. This track does
not need robot power, a STOP deployment or new head hardware.

**Track B, independent maintenance window:** deploy the reviewed STOP candidate
under the wired protocol and qualify changed ingresses motor-off. Keep it separate
from stream edits and never reset/flash implicitly to test media.

**Track C, before public production use:** contain or retire the legacy browser
credential path, review dependency upgrades, and add repository verification/CI.
It need not block offline Track A when that legacy app is not part of the path.

**After the public activity seam works:** connect the selected jabberWERK batch
audio/shared clock, then avatar fallback; qualify physical-head control only
after its measurements. Private lifecycle/cancellation/soak acceptance comes
before unattended/public streaming. No whole-project completion percentage is
supported by the evidence.
