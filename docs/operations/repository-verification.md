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
| `dispatcher` | Seven CLI regressions and two dependency-proxy policy tests | Python 3; failure propagation, stop-on-inner-failure and adversarial proxy targets |
| `media` | Unmodified media gate: three locked Python projects, snapshot fixture, shell syntax, headless Godot producer/consumer fixture | UV, Python 3.12, `FURBOMEK_GODOT` pointing to Godot 4.7; no capture or live services |
| `robot-native` | Existing actuator-disabled native C++ tests and source safety gate | C++17 compiler (`CXX`), ripgrep; diagnostic protocol only, not installed firmware or HIL |
| `guard-native` | Existing guard tests, STOP routes, driver lifecycle assertions and source safety gate | Existing build requires pinned FNHR/vendor archives and Arduino core even in native mode; `FNHR_DIR`, `FREENOVE_ROOT`, `ARDUINO_CORE_DIR` retain their existing meanings |
| `robot-avr` | Existing diagnostic AVR build and timer-order checks | Extracted `AVR_ROOT`; output only in a disposable directory, no device action |
| `guard-avr` | Existing guarded AVR build | Both vendor inputs and exact AVR toolchain required by its build script; no installation/flash claim |
| `legacy` | Existing `npm run build` | Preinstalled locked root/server dependencies; existing failures remain visible |

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
Only the candidate directory is supplied as data to the trusted helper. Changes
to worker/proxy code in a PR cannot replace the helper that tests that PR.

**Bootstrap gate:** the current accepted main does not contain these helpers.
This first adoption therefore intentionally fails media/legacy before executing
candidate helpers. It requires two stages: independent review and explicit
acceptance of the bootstrap policy/helpers, then a separate candidate run using
those now-accepted helpers and observed containment/product evidence. This PR does
not authorize that merge or policy activation. Never fall back to candidate helpers
or regard this PR's own workflow results as independent trust approval.

Media and legacy candidate code now run only in official Python 3.12.11 and Node
22.16.0 images pinned to Linux amd64 content digests. Workers run as UID/GID 1000
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
or invoke its build backend, and caches Hatchling 1.27.0 for the later offline
editable-project build. Npm lifecycle scripts remain disabled during provisioning.
The test/build worker uses `--network none`; Python also uses `UV_OFFLINE=1`.
The actual frozen media gate and Nuxt build run there without weakening tests.

The media job uses UV 0.11.7 and the existing Godot 4.7.2 archive URL/hash from
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

## Implementation evidence

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
- The final accepted-base bootstrap gate is expected to block media/legacy until
  independently accepted helpers exist on main. Exact-revision blocked evidence,
  helper/network qualification and independent rereview remain required. Vendor/AVR
  coverage also remains outstanding; this is not full issue-4 acceptance.

## Changelog

- 2026-10-30: added isolated media/legacy provisioning and offline execution after
  independent review; retained all existing product checks and explicit coverage gaps.

TLA+/Gherkin are not applicable to this build-infrastructure dispatcher; the
executable CLI regressions test failure propagation and adversarial unknown
arguments directly. Canonical scope and live status stay on issue 4, under the
coordination PW-0 product-verification follow-up, not a second task queue.
