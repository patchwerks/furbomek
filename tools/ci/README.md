---
created: 2026-10-29T17:49:18Z
branch: codex/4-ci-bootstrap
author: Codex
status: active
---

# CI helper bootstrap candidate

This is the helper-only prerequisite for [verification PR #18](https://github.com/patchwerks/furbomek/pull/18), referencing [issue #4](https://github.com/patchwerks/furbomek/issues/4). It adds no workflow, verification dispatcher, automatic trust pin or activation. The initial worker and proxy were extracted from source-reviewed revision `59f4f4f4ddec2b3eb8c9eb096e811f7813a889c5`. The worker now includes the Python provisioning correction below; source review does not qualify runtime behavior or grant independent maintainer approval.

`worker.sh media|legacy CANDIDATE_DIRECTORY` is proposed trusted orchestration for a disposable Linux CI host with Docker. It requires a separate candidate checkout. The proxy is loaded only from the helper's own checkout. Candidate source is mounted read-only, copied into bounded scratch, and executed as an unprivileged container user without runner credentials, host home or a Docker socket. Dependency provisioning uses an isolated network and an exact HTTPS registry allowlist; actual candidate tests/builds use a fresh network-none worker. Images and the Godot download are pinned. Package hooks/source builds are disabled during networked provisioning.

The candidate must supply `tools/verify.sh` and its existing lockfiles/product checks. This helper-only checkout intentionally has no dispatcher, and is not a standalone product-verification command. The invoking accepted workflow must select an accepted helper revision separately from candidate code and fail closed if helpers are absent. Candidate filenames, output or a green run cannot select or approve that revision.

## Python provisioning boundary

`provision-python.sh SOURCE ENV_ROOT CACHE UV PYTHON` is mounted read-only from
that same accepted helper checkout. The production caller fixes the interpreter
to `/usr/local/bin/python3` and uv to `/scratch/bootstrap/bin/uv` (0.13.6).
Explicit paths also permit controlled offline regression fixtures. They are
trusted caller arguments, never candidate-selected settings.

Each service sync uses `--no-config`, `--python`, `--frozen`,
`--no-install-project` and `--no-build`. The helper creates `/scratch/python-envs`
and `/scratch/uv-cache` with fail-if-existing `mkdir`; candidate `.venv`,
`.python-version`, uv configuration and startup paths cannot choose the
provisioning interpreter or environment. Projects resolving outside the copied
source are rejected. Each service environment receives one sync; populated
dependency environments are not queried again while registry egress is enabled.
Script sync uses the same explicit interpreter and fresh helper-owned cache.
Hatchling wheel preparation selects the base interpreter explicitly as well.

Only in the later network-none container are copied service `.venv` entries
replaced with links to the prepared external environments. The cache persists
for the offline script run. The unchanged candidate dispatcher remains the
product check. Helper/candidate checkout separation resolves physical paths,
including symlink aliases. These changes do not activate or accept the helper.

## Acceptance sequence

1. An independently authorized maintainer reviews this exact helper/policy revision and records explicit bootstrap acceptance under [the coordination trust policy](https://github.com/patchwerks/patchwerks/blob/b99937e5f22ff34455723aaca667b394bd2be86e/docs/trust.md). Advisory agents sharing the author's GitHub principal cannot supply that approval. No acceptance, merge or protection changes are performed by this preparation.
2. After authorized bootstrap acceptance and publication on the accepted base, a separate candidate run must observe proxy readiness, direct-egress denial, forbidden-host denial, allowed registry provisioning, lifecycle-hook suppression, credential/socket absence, network-none test execution and the unchanged product checks. Record the exact candidate/helper/image revisions and failures before accepting workflow activation. PR #18 remains dependent on this gate.

## Observed evidence and limits

The extracted helpers originate from PR #18's failed-closed revision. Its [run 40922998072](https://github.com/patchwerks/furbomek/actions/runs/40922998072) passed native safety, while media/legacy stopped before candidate execution because accepted main lacked helpers. The earlier containment smoke at `ab47ca7352dc6149de56d4f8308689c2870a139f` ([run 40922381063](https://github.com/patchwerks/furbomek/actions/runs/40922381063)) stopped at proxy connection refusal before dependency provisioning or tests. Added listener readiness and diagnostics have not been operationally qualified. Earlier green product checks predated the required isolation and are not containment evidence.

Observed for this split: all seven offline tests passed with an empty environment and a local sandbox denying network access, private-home/device reads and source writes. Shell syntax and whitespace checks passed. Offline check commands:

```sh
python3 -B -m unittest discover -s tools/tests -p 'test_dependency_proxy.py' -v
python3 -B -m unittest discover -s tools/tests -p 'test_ci_worker.py' -v
python3 -B -m unittest discover -s tools/tests -p 'test_python_provision.py' -v
bash -n tools/ci/worker.sh tools/ci/provision-python.sh
```

These check exact registry authorities, private-address rejection before connection, and malformed worker inputs before any Docker call. Run in a credential-free restricted worker. They do not establish Docker networking, package installation, Godot execution or product verification. No local Docker runtime was available for this preparation. No hardware, OBS, Hermes or live service is part of this bootstrap. Rollback before activation removes these standalone files; any later activation needs its own reviewed rollback.

The provisioning regressions require exact uv 0.13.6 and otherwise skip with an
explicit version message. They invoke the actual trusted helper on synthetic
empty locked projects, hostile interpreter/configuration/startup markers, reused
state and escaping symlinks. A local wheel containing a startup `.pth` proves
that installed dependency startup remains dormant through provisioning and runs
only when deliberately invoked afterwards in the offline test. A snapshot-script
fixture imports a synthetic local-wheel dependency through `uv run --frozen`
with offline mode and the same helper-owned cache, and confirms it uses the
environment prepared by the helper. These fixtures
must themselves run in a credential-free network-denied boundary; they do not
qualify registry egress or full Docker containment.

## Correction verification — 2026-10-30

At helper revision `b04523abf79f22b750a3cdb579f2169a717e1b38`, all **14**
helper tests passed with **zero skips** using exact uv 0.11.7 and the pinned
Python 3.12.11 Linux image. The test-only workflow revision was
`ce87ee3964a1c2fefc5a28e08e07516b3ae56f1a`;
[run 40952027806, job 123722330403](https://github.com/patchwerks/furbomek/actions/runs/40952027806/job/123722330403)
records both the original vulnerable marker characterization and the corrected
helper regressions. The original `.venv` and `.python-version` probes created
their markers; the corrected helper passed the hostile interpreter/configuration,
startup `.pth`, fresh-state, symlink and offline script-cache tests.

These synthetic fixtures ran as an unprivileged user in a read-only,
network-none container, with no host home, credentials, devices or Docker socket
mounted. Independent advisory source review found no blocking defect in this
scoped correction. Local input/proxy tests also passed (8); local uv 0.13.6
correctly skipped the exact-version class and is not the qualifying evidence.
Shell syntax and whitespace checks passed.

This establishes the bounded interpreter-selection correction, not operational
acceptance of the full worker. The full Docker/proxy provisioning path, registry
routing/denials and unchanged product checks still require the separate acceptance
sequence above. No helper was activated, trust pin changed or PR merged.


## Node compatibility pin — 2026-10-30

The legacy worker now pins the official `node:26.7.0-bookworm` image at index
digest `sha256:e929171d35b9df7773a3ec5b068e387fa109441dc90f91e6560af5d39b7e9bf1`.
This replaces Node 22.16.0, which is below the pending [Nuxt 4 upgrade's](https://github.com/patchwerks/furbomek/pull/28)
engine requirement (`^22.22.3 || ^24.15.0 || >=26.0.0`). Node 26.7.0 satisfies
that range and matches the version used for that upgrade's local checks.

**Observed:** the [Docker official Node registry manifest](https://registry-1.docker.io/v2/library/node/manifests/26.7.0-bookworm)
returned that index digest; the response body's SHA-256 matched. Its Linux amd64
manifest is `sha256:158304f335472bdd3fe88be1c4d37e5d83f3d1fd57da656863c24e7d889e4dea`;
the referenced image configuration declares `NODE_VERSION=26.7.0`. Manifest and
configuration body hashes matched their referenced digests. The index also
contains Linux arm64/v8 and ppc64le images. These are registry metadata checks,
not execution of the image.

The Python helper, Python image and all container/network/proxy boundaries are
unchanged. Local credential-free, network-denied proxy/input tests passed (8),
as did shell syntax and whitespace checks. No local Docker runtime was available,
so this pin has not qualified the full Docker/proxy path or Nuxt build in that
image. The existing Python correction's exact-version regression evidence above
is unchanged; this Node-only update does not repeat or extend it. Independent
review and the separate acceptance sequence still apply before activation.

## Review corrections — 2026-10-30

The current helper requires a stable **Docker Engine server 28.0.0 or newer**.
Docker's [28.0.0 release notes](https://docs.docker.com/engine/release-notes/28/#2800)
introduce `gateway_mode_ipv4=isolated` for internal bridge networks. The helper
checks the server version before pulls, resource creation, or cleanup registration;
unavailable, malformed, prerelease and older versions fail closed. This minimum
is a feature prerequisite, not operational qualification of every Docker version.

The proxy starts attached only to the isolated worker network. Its trusted
launcher resolves its own container hostname to a numeric IPv4 address and the
proxy requires an explicit validated private, non-loopback `--bind-address`.
Readiness probes use the Docker-inspected address on that exact internal network.
Only after readiness succeeds does the helper attach the default bridge for
registry egress. The listener remains bound to its original internal address;
there is no wildcard listener, published port or fixed subnet allocation. This
removes the listener from the egress interface; it does not claim that a
privileged Docker host cannot access container addresses.

Tunnels now expire after 120 seconds without successfully forwarded bytes, with
a separate 900-second maximum lifetime. Successful traffic resets only the idle
clock. Each blocking operation is limited by its remaining idle/maximum budget
and the existing 15-second I/O ceiling. These bounds accommodate active transfers
beyond the former absolute two-minute cutoff while limiting connection lifetime;
they are not a measured registry throughput guarantee.

Current bootstrap uv is **0.13.6**. The preceding 0.11.7 evidence remains historical
and does not qualify the new version. PyPI metadata for 0.11.7 reports
[wheel executable overwrite](https://github.com/astral-sh/uv/security/advisories/GHSA-4gg8-gxpx-9rph)
and [compromised vendored CA trust](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62)
advisories, fixed in 0.11.15 and 0.13.4 respectively. Exact-version regression
fixtures now require 0.13.6.

Both `bootstrap-requirements.txt` and `build-requirements.txt` are mounted from the
trusted helper checkout and installed with `--require-hashes`, `--no-deps` and
`--only-binary=:all:`. Candidate requirement files cannot select these tools.
The build manifest preserves the existing verified six-package set (hatchling
1.27.0, editables 0.5 and four pinned dependencies), copied from the previously
reviewed build manifest at revision
`a8c01317fa739c29cec90060edf92056974b01b0`; its file SHA-256 is
`3da3b9055958e002237bcd51cbd3f627487677ce129b103db070592e13245602`.
All artifact hashes were checked against official PyPI version metadata on
2026-10-30: [uv](https://pypi.org/pypi/uv/0.13.6/json),
[editables](https://pypi.org/pypi/editables/0.5/json),
[hatchling](https://pypi.org/pypi/hatchling/1.27.0/json),
[packaging](https://pypi.org/pypi/packaging/26.3/json),
[pathspec](https://pypi.org/pypi/pathspec/0.12.1/json),
[pluggy](https://pypi.org/pypi/pluggy/1.7.0/json) and
[trove-classifiers](https://pypi.org/pypi/trove-classifiers/2025.3.19.19/json).
The uv manifest includes Linux x86_64 and arm64 wheels, but the existing Godot
artifact remains x86_64; this does not establish arm64 product support.

New synthetic tests execute the production relay with fake sockets/clock, mock
listener construction, and run the worker against an argument-recording fake
Docker/download toolchain. They cover timeout renewal and ceilings, invalid
binding rejection, version rejection before mutations, internal bind/readiness
before external attachment, trusted manifest mounts, and final network-none
execution. Faked downloads/checksums do not qualify real downloads or installer
hash rejection. All real Docker networking, proxy reachability/denials, registry
installation and unchanged product checks remain in the separate acceptance
sequence. No workflow or accepted helper pin is activated by these changes.

Observed locally for these corrections: **22 tests passed** (15 proxy/relay/bind,
7 input/fake-runtime orchestration) under the existing credential-free macOS
boundary denying network, private-home/device reads and source writes, using
Python 3.12.16. Shell syntax and whitespace checks passed. The attempted full
28-test run with exact uv 0.13.6 reached the existing Linux-only `realpath -e`
command and failed four provisioning cases on macOS; two provisioning rejection
cases passed. This is an explicit local platform limitation, not a successful
new-version provisioning qualification. A Linux run using the pinned Python
3.12.11 image is still required for all exact-version regressions.


## Exact-version Linux fixture — 2026-10-30

At helper revision `267d68f248c78f0e9fbe4a72625f6b527f3a2916`, the hosted Linux fixture passed **28 tests with
zero skips**, using exact uv 0.13.6 and the pinned Python 3.12.11 image:
[run 40985799560, job 123836400297](https://github.com/patchwerks/furbomek/actions/runs/40985799560/job/123836400297).
This supplies the new-version Linux provisioning regression evidence missing
from the local macOS attempt above. It does not qualify the full worker,
registry routing, proxy containment or product checks.

The subsequent build-input target installation now explicitly uses
`--link-mode copy`. Separate build-input files avoid sharing cache hardlinks
with service environments, which can cause the later offline copy to fail
because source and destination are the same file. The fake-worker argv test
requires this flag. A fresh immutable Linux fixture rerun at final code revision
`71a0b0cb1f59361df26fb550e4cf8a8e689387f1` passed all **28 tests with zero skips**:
[run 40986264572, job 123837909390](https://github.com/patchwerks/furbomek/actions/runs/40986264572/job/123837909390).
Test-only workflow revision: `b71ac458a8bc50796695072310da78babb672981`.
No workflow/helper activation or full-worker acceptance follows from it.

## Scratch lifetime correction — 2026-10-30

**Observed:** the first accepted-base product run for PR #18 at
`69e32e017b29bbdb604a4a871fab97533322deb3`, using accepted helpers from main
`9aa7546`, passed direct-egress denial, forbidden-proxy-host rejection and the
allowed PyPI request. Media also installed hash-pinned uv successfully. Both
media and legacy then failed because `/scratch/source` had disappeared:
[run 41027114292](https://github.com/patchwerks/furbomek/actions/runs/41027114292).
The tmpfs-backed local Docker volume was unmounted when the last ephemeral
worker exited; a later mount started with empty contents. No product-test pass
is implied by the successful networking/bootstrap steps.

The correction keeps one dedicated trusted container holding the bounded 4 GiB
scratch mount throughout the disposable worker phases. It runs only `sleep
infinity` from the existing pinned Python image: UID/GID 1000, network none,
read-only root, all capabilities dropped, no privilege regain, 0.1 CPU, 32 MiB
memory and eight processes. It receives only the scratch volume, with no source,
credentials, host paths, socket, proxy network or candidate command. Cleanup
removes it before removing the volume. Actual candidate provisioning/execution
boundaries and all dependency pins are unchanged.

**Measured:** all nine input/fake-Docker orchestration tests passed in the local
credential-free, network-denied sandbox. They verify keeper creation before any
worker, the same scratch mount across phases, resource restrictions, cleanup
ordering, and failure handling. They do not execute real Docker.

A separate fixed inline Linux storage probe at
`31ca9436088761d2b70435ce706fafac6814f9e0` passed
[run 41028202341](https://github.com/patchwerks/furbomek/actions/runs/41028202341):
without a keeper the marker disappears, with the keeper it survives between
workers, removing the final keeper discards it, and volume removal is verified.
That test uses the same image, mount options and container restrictions, without
checking out or running candidate helpers. It qualifies the storage primitive,
not the revised full helper or media/Nuxt products.

This is a new helper revision requiring independent acceptance. PR #18 continues
to select accepted-base helpers and must not substitute this candidate to obtain
a green result. After acceptance/publication, rerun the full media and legacy
jobs and record their exact helper/candidate revisions. No trust selection,
workflow activation, merge, runtime deployment or physical access is authorized
by these tests.

The exact corrected helper at `fb93566ffbaf4cfb1b8b52716522ae6c86aae67b`
also passed **30 Linux fixture tests with zero skips**, using pinned Python
3.12.11 and exact uv 0.13.6 in a non-root, read-only, network-none container
without Docker socket access:
[run 41028713745](https://github.com/patchwerks/furbomek/actions/runs/41028713745),
test-only workflow `cbc46f63a83ae8991a8c25ab7b4424655d909f42`. These include
nine worker, fifteen proxy and six provisioning regressions. Integration of
accepted main `26f4bdb` leaves those helper/test source files unchanged.

## Changelog

- 2026-10-30: corrected scratch mount lifetime for issue #4 / PR #31; recorded
  the observed product-run failure, fixed storage probe and 30-test Linux fixture
  evidence. Full worker qualification still requires independent acceptance.
- 2026-10-31: measured scratch ownership/write failure with default copy-up and
  successful `volume-nocopy` preservation under production working-directory
  settings; recorded the fixed Docker probe and nine-worker-fixture evidence.
  Full media/Nuxt product qualification remains separate.

## Scratch permissions investigation — 2026-10-31

**Observed:** after accepting the keeper correction on main `c80e1bee`,
PR #18's media and legacy workers both stop at `cp -R /source/. /scratch/source`
with permission denied, before candidate execution. The earlier storage probe
omitted the production worker's `--workdir /scratch`; its passing result did not
qualify that launch configuration.

**Measured in the fixed probe:** on Docker Engine **28.0.4**, both pinned
Python 3.12.11 and Node 26.7.0 worker images with production
`--workdir /scratch` observed UID/GID **0:0**, mode **755**, and
`MARKER_WRITE_DENIED` for a fresh default-copy-up volume despite its explicit
1000:1000/mode 0700 tmpfs options. With `volume-nocopy` on both the pinned Python
keeper and worker mount, both images observed UID/GID **1000:1000**, mode **700**,
`MARKER_WRITTEN` and `CROSS_PHASE_MARKERS_PRESERVED`. All probe containers and
volumes were removed and cleanup was verified. This demonstrates the default
copy-up ownership failure and nocopy correction for this Docker version, pinned
image pair and working-directory configuration; it is not a claim about every
Docker version or image.

The correction changes only the two scratch mount options in the worker. User,
capability, privilege, host-mount, network, accepted-helper selection and candidate
execution boundaries are unchanged. The fixed inline storage job checks fresh
volumes and marker write/read persistence across disposable phases without
checking out or executing candidate code. All probe containers are non-root,
read-only, network-none and resource-bounded, with no credentials, host directory
or Docker socket mounted.

Evidence: [run 41214876308](https://github.com/patchwerks/furbomek/actions/runs/41214876308),
[storage job 124577220132](https://github.com/patchwerks/furbomek/actions/runs/41214876308/job/124577220132),
for source head `fab5c3071df85f2be2e3e2ecac7abe978be904c3` and tested PR merge
`ec1f62897b4567a7c0d0657ad5bb9b4efd23aa43` into accepted main
`c80e1bee0144c1844047e78c46e32f855b22d309`. The same run's separate worker-fixture
job passed **9 tests with zero skips**. It executes the argv regressions inside
the pinned Python container with a clean environment, network none, a read-only
root and only the worker/test files bound read-only. Candidate test code receives
no Docker socket or host home and never executes on the Docker host. Those
fixtures check both scratch mounts, production working directory and existing
orchestration boundaries; the fixed storage job supplies the actual Docker
behavior evidence. Current-head CodeQL checks also passed.

Local Docker was unavailable. The local confined test attempt stopped at
`sandbox_apply: Operation not permitted` before Python started, so no local
runtime or unit-test pass is claimed. Shell syntax, Python parsing and whitespace
checks passed. The hosted results above are tied to their recorded revisions;
this evidence-only documentation update does not itself obtain fresh approval.

The publishing account's advisory review is not independent maintainer
acceptance. Independent exact-head acceptance and publication on accepted main
must precede another PR #18 product run using accepted-base helpers. These
results qualify the bounded storage correction and worker fixtures, not full
media/Nuxt products, registry provisioning, live integration or deployment.
