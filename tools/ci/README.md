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
to `/usr/local/bin/python3` and uv to `/scratch/bootstrap/bin/uv` (0.11.7).
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

The provisioning regressions require exact uv 0.11.7 and otherwise skip with an
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
