---
created: 2026-10-29T16:55:07Z
branch: codex/4-reproducible-ci
author: Codex
status: active
---
# Non-live repository verification

This implements the verification/CI slice of [issue 4](https://github.com/patchwerks/furbomek/issues/4).
It is independent of the separately claimed Simulation Lab and does not consume
unmerged simulation code. The existing `tools/verify-media.sh` is unchanged.

Run `bash tools/verify.sh --help` for component selection. With no arguments it
runs the complete inventory, continues after failures, and reports each component
as PASS, FAIL or UNAVAILABLE. Exit 0 means every selected component passed; 1
means at least one failed; 2 means a prerequisite is missing (or invalid usage)
with no other failure. A partial selection is never a full-repository pass.
Subcommand output and its original exit code remain visible.

| Component | Actual verification | Inputs / limits |
|---|---|---|
| `dispatcher` | Eleven CLI regressions and fifteen dependency-proxy tests (26 total) | Python 3; failure propagation, explicit prerequisite paths, stop-on-inner-failure and adversarial proxy targets |
| `media` | Unmodified media gate: three locked Python projects, snapshot fixture, shell syntax, headless Godot producer/consumer fixture | UV, Python 3.12, `FURBOMEK_GODOT` pointing to Godot 4.7; no capture or live services |
| `robot-native` | Existing actuator-disabled native C++ tests and source safety gate | C++17 compiler (`CXX`), ripgrep; diagnostic protocol only, not installed firmware or HIL |
| `guard-native` | Existing guard tests, STOP routes, driver lifecycle assertions and source safety gate | Existing build requires pinned FNHR/vendor archives and Arduino core even in native mode; explicit `FNHR_DIR`, `FREENOVE_ROOT`, `ARDUINO_CORE_DIR` required |
| `robot-avr` | Existing diagnostic AVR build and timer-order checks | Extracted `AVR_ROOT`; output only in a disposable directory, no device action |
| `guard-avr` | Existing guarded AVR build | Both vendor inputs and exact AVR toolchain required by its build script; no installation/flash claim |
| `legacy` | Existing `npm run build` | Preinstalled locked root/server dependencies; existing failures remain visible |

The dispatcher requires nonempty `FNHR_DIR`, `FREENOVE_ROOT` and
`ARDUINO_CORE_DIR` for both guard components, and nonempty `FURBOMEK_GODOT` for
media. It then checks the required files or executable. There are no implicit
operator-host paths. Missing variables or paths return internal prerequisite
status 125, reported as UNAVAILABLE and aggregate exit 2 when no check fails.
Quoted explicit paths may contain spaces; none of these inputs authorizes a
device action.

The native camera producer's full host build is deliberately outside this
entrypoint: `tools/kinect2/build-host.sh` provisions host dependencies and models.
Its synthetic snapshot consumer tests are covered by `media`; this does not
claim the native camera binary or physical capture has been rebuilt or qualified.

## CI and isolation

`.github/workflows/verify.yml` runs three independent GitHub-hosted jobs with
read-only permissions, no persisted checkout credential, immutable action SHAs,
explicit runtime versions and bounded job timeouts. No secrets, self-hosted
runners, host/device mounts or production services are configured. Ordinary
`pull_request` is used, never `pull_request_target`.

The media/legacy orchestration and proxy must come from a separate **accepted-base**
checkout, not the candidate. Pull requests target main and select their exact base
SHA; pushes to main use the preceding revision; manual dispatch selects the default
branch rather than an arbitrary dispatch ref. An absent/invalid base fails closed.
Only the candidate directory is supplied as data to the selected helper.
With this workflow unchanged, candidate worker/proxy edits cannot replace that
accepted-base helper selection. The workflow itself is candidate-editable:
accepted-base checkout protects helper selection only while those workflow
instructions remain intact. This PR's workflow is advisory and provides no
independently enforced policy boundary or required-check protection against a
candidate changing the workflow. Independent workflow review remains necessary;
no secrets are supplied to these jobs.

**Current bootstrap gate:** accepted main `9aa7546` includes the merged PR #22
helpers, reconciled into this candidate without changing their accepted contents.
The former missing-helper bootstrap blocker is resolved. Full media/legacy
Docker/proxy runtime qualification using those accepted helpers remains pending;
helper availability and unit tests do not establish that result. Never fall back
to candidate helpers or treat this PR's own workflow results as independent
policy approval. The accepted helper fixture suite contains 28 tests: fifteen
proxy, seven worker and six exact-uv provisioning regressions. The dispatcher
runs its eleven CLI tests plus the fifteen proxy tests; it does not run that
entire helper suite.

Media and legacy candidate code now run only in official Python 3.12.11 and Node
26.7.0 images pinned to Linux amd64 content digests. Workers run as UID/GID 1000
with no capabilities, no privilege escalation, read-only root/source mounts,
bounded tmpfs scratch and CPU/memory/process limits. The source is copied byte-for-
byte into disposable scratch so unchanged existing tools can write their normal
environments and build outputs. A Git diff checks tracked content before tests.
No runner environment, home, credentials, Docker socket or writable host paths
are forwarded. Workers are destroyed between provisioning and test/build phases.

Provisioning uses a Docker internal network in isolated gateway mode, so it has
no Internet or host bridge gateway. Its only egress is a separate non-root
CONNECT proxy accepting port 443 at exactly `pypi.org`, `files.pythonhosted.org`
and `registry.npmjs.org`, resolving only public addresses. Connection lifetimes,
resources and request parsing are bounded. Tests reject hostname suffixes,
credentials in authorities, private literals and alternate ports. Each real job
also asserts direct Internet access and a forbidden proxied hostname fail before
installing dependencies. No package-registry credentials are provided.

Python provisioning installs wheels only, does not install the candidate project
or invoke its build backend. Helper-owned requirements pin and hash all six
offline build inputs: editables 0.5, Hatchling 1.27.0, packaging 26.3, pathspec
0.12.1, pluggy 1.7.0 and trove-classifiers 2025.3.19.19. They are installed as
wheels with hashes required and dependency resolution disabled for the later
offline editable-project build. Npm lifecycle scripts remain disabled during provisioning.
The test/build worker uses `--network none`; Python also uses `UV_OFFLINE=1`.
The actual frozen media gate and Nuxt build run there without weakening tests.

The accepted helper uses uv 0.13.6 and the existing Godot 4.7.2 archive URL/hash from
`tools/kinect2/build-host.sh`. Project dependencies remain frozen to their
committed UV locks. Native CI uses the official GCC 13.3.0 Linux amd64
image pinned to its content digest and ripgrep 15.1.0 pinned to its release hash.
Only the checkout and scanner are mounted read-only; the test container runs as
the non-root runner UID with no network, credentials, host/device/socket mounts,
capabilities, or privilege escalation. Temporary build files use a bounded tmpfs;
CPU, memory and process counts are bounded. The image is provisioned before test
execution. Runner OS is Ubuntu 24.04; the hosted image is maintained by GitHub
and is not a byte-reproducible VM image. No `continue-on-error` converts legacy
debt into success.

Guard/native and AVR qualification are **not covered by the hosted jobs** until
the existing pinned vendor inputs/toolchain can be provisioned through an
accepted, licensed source. The default local inventory exposes those missing
prerequisites instead of silently skipping them. No vendor code is copied into
this change. Source checks or diagnostic tests do not replace those builds.

The dispatcher is not a sandbox. Candidate tests and package installs execute
code and belong only in disposable credential-free workers without production
network or device access. Provision dependencies separately where network access
is required. Never use an operator's live robot/media host to test arbitrary PRs.
Workflow changes themselves require independent review against trusted policy;
a candidate workflow's green result does not approve its own policy changes.

## Legacy debt and acceptance

`npm ci` normally triggers a root postinstall that builds Nuxt and installs the
server dependencies. CI disables implicit hooks and runs the desired build
explicitly. This may reveal existing lock, native-module, generated-file or
application failures. Report the original failure; do not upgrade packages,
enable privileged hooks or weaken tests to make this verification PR green.
Dependency remediation is tracked separately in
[issue 13](https://github.com/patchwerks/furbomek/issues/13).

Issue 4 remains open until actual checkout and hosted workflow evidence is
reviewed. No new required-check rule or merge authority is configured here.
Rollback is reverting this PR's dispatcher, tests, workflow and documentation;
the existing media script and product runtime remain unchanged.

## Historical implementation evidence

The following records describe earlier revisions and their then-current helper
versions and counts. They do not qualify the current accepted-helper runtime.

- Base: `9347304e866ca90e8eec2d85f3bd3c41002d9a42`.
- Red: CLI regression cases initially had no dispatcher (first five failed
  with missing-file errors); the inner-component failure case was added after
  implementation to prevent Bash `errexit` suppression.
- Green: seven dispatcher and two proxy-policy tests passed locally; shell syntax
  checks passed.
- Actual checkout inventory: `dispatcher` passed; `media`, `guard-native`, both
  AVR builds and `legacy` reported missing prerequisites and aggregate exit 2.
  UV, pinned vendor inputs, AVR_ROOT and installed npm dependencies were absent.
- Native test execution inside a local deny-by-default credential-free sandbox
  could not start (sandbox process exited 134 before test output). No native
  product pass is claimed. Hosted disposable CI is the next verification surface.
- First hosted run at `808c72b1cf22f1d3c59b953f041d7c9fa8407a8c`: locked
  media fixtures, legacy Nuxt build, and all existing CodeQL analyses passed.
  Native CI failed at the GCC 13.3.0 version assertion before test execution;
  the mutable hosted compiler was not the required version. The correction pins
  an official compiler image rather than relaxing the version requirement.
- The next revision, `38a1cafd8552673a74baa39a5bafa9d9edbacd0a`, passed all three
  hosted jobs and CodeQL. Independent review correctly found that media/legacy
  candidate code still ran directly on the hosted runner. Those green results
  did not qualify the required credential-free execution boundary.
- Containment smoke at `ab47ca7352dc6149de56d4f8308689c2870a139f` passed native
  safety and CodeQL, but both media/legacy stopped at proxy connection refusal
  before dependency provisioning or product tests. Direct external DNS failed;
  that alone does not prove the whole network policy. A bounded listener readiness
  gate and safe proxy failure diagnostics have been added; their runtime behavior
  remains unqualified. This smoke also used candidate helper code and is not
  accepted enforcement evidence.
- At that revision, the accepted-base bootstrap gate was expected to block
  media/legacy until independently accepted helpers existed on main. Accepted main
  now contains them, as recorded above. Full helper/network runtime qualification,
  independent rereview and vendor/AVR coverage remain outstanding; this is not
  full issue-4 acceptance.

## Changelog

- 2026-10-30: added isolated media/legacy provisioning and offline execution after
  independent review; retained all existing product checks and explicit coverage gaps.
- 2026-10-30 review follow-up: reconciled accepted main's helpers, documented
  candidate-editable workflow limits, and required explicit vendor/Godot paths.
  Added missing-variable and space-containing-path CLI regressions; current
  execution evidence is pending verification of this revision.

TLA+/Gherkin are not applicable to this build-infrastructure dispatcher; the
executable CLI regressions test failure propagation and adversarial unknown
arguments directly. Canonical scope and live status stay on issue 4, under the
coordination PW-0 product-verification follow-up, not a second task queue.
