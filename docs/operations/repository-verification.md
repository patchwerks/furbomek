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
| `dispatcher` | Seven CLI regression tests using disposable fixture checkouts | Python 3; tests fail/pass/unavailable propagation and stop-on-inner-failure |
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

The media job uses Python 3.12.11, UV 0.11.7, and the existing Godot 4.7.2 archive
URL/hash from `tools/kinect2/build-host.sh`. Project dependencies remain frozen
to their committed UV locks. Native CI uses the official GCC 13.3.0 Linux amd64
image pinned to its content digest and ripgrep 15.1.0 pinned to its release hash.
Only the checkout and scanner are mounted read-only; the test container runs as
the non-root runner UID with no network, credentials, host/device/socket mounts,
capabilities, or privilege escalation. Temporary build files use a bounded tmpfs;
CPU, memory and process counts are bounded. The image is provisioned before test
execution. Runner OS is Ubuntu 24.04; the hosted image is maintained by GitHub
and is not a byte-reproducible VM image. The legacy job pins
Node 22.16.0, installs the npm locks with lifecycle hooks disabled, then explicitly
runs the existing build. No `continue-on-error` converts legacy debt into success.

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
- Green: seven tests passed locally; shell syntax check passed.
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
- Final-revision hosted results remain pending. Vendor/AVR coverage and independent
  review remain outstanding, so this is not full issue-4 acceptance.

TLA+/Gherkin are not applicable to this build-infrastructure dispatcher; the
executable CLI regressions test failure propagation and adversarial unknown
arguments directly. Canonical scope and live status stay on issue 4, under the
coordination PW-0 product-verification follow-up, not a second task queue.
