---
created: 2026-11-02T09:29:44Z
branch: codex/32-contributor-kit
author: patchWERKS / Codex
status: active
---
# Presentation pack contributor starter record

This is the bounded contributor starter slice of [issue 32](https://github.com/patchwerks/furbomek/issues/32).
It was prepared on `codex/32-extension-contract` at
`8c38c3fd814cc7dfdfd25ee706e5718f28f0de28` (PR 41). That core was accepted
and merged on 2026-11-04 at `ccad3d5c9cd9d52c83af20e21163dbd4b0ea8463`.
This kit remains an unapproved draft requiring separate acceptance.
The original preparation product policy baseline was
`cdd9147fac9141fa0c75b5058f9dce46c7885188`; the coordination foundation is
`patchwerks/patchwerks@b99937e5f22ff34455723aaca667b394bd2be86e`.
The separate viewer candidate in PR 42 is unchanged.

## Candidate scope

The [contributor guide](../contributing/presentation-packs.md) supplies complete
JSON examples and direct Node commands. The package adds neutral, curious and
acknowledge examples, plus tests for exact inventory, regular bounded files,
strict parser acceptance, identities/capabilities, cue timing, expiry, reset,
end clamping, backwards seeks, guide JSON fidelity, documented command text
and relative links. The seven contributor tests live in
`docs/contributing/tests/presentation-packs.test.mjs`, outside the independently
qualified package-only suite. Existing parser/schema/loader implementations and
the accepted package-only workflow are unchanged.
No install scripts or new dependencies are required.

## Verification procedure and limits

The advisory workflow is
[`.github/workflows/presentation-pack-examples.yml`](../../.github/workflows/presentation-pack-examples.yml).
The supervising publisher manually reviews the worker boundary before advisory
isolated execution. Independent workflow review is still required before main
acceptance. Advisory execution is not an accepted privileged enforcement gate
and cannot approve its own policy or product integration.

The workflow checks out the exact pull request head, checks Git modes and
filesystem types, rejects symlinks/gitlinks and oversized inputs, then mounts
only the package, contributor documentation and `docs/agents` subtrees read-only.
The third mount is documentation data for relative-link checks; it adds no code
execution or host authority. Inputs are
limited to 500 files, 1 MiB each, and 16 MiB combined. Fixed images are pulled
outside the worker; candidate commands execute only inside it.

Workers use digest-pinned Node `22.22.3` and `26.7.0` Bookworm images with no
network, read-only root, dropped capabilities, no-new-privileges, UID 1000,
2 CPUs, 1 GiB RAM, 128 PIDs and a 512 MiB nosuid/nodev temporary filesystem.
The environment is cleared and HOME is an empty temporary directory. No host
home, Git credentials, `.git`, host devices, Docker socket or entire checkout is
mounted. Container-provided basic devices are not host-device access grants.

The worker executes the guide's three marked shell blocks once each: starter
checks, complete package tests with `--experimental-vm-modules`, and the
`loadPackFile` validation CLI against the neutral example. Markdown shell is
candidate code and is never extracted or executed on the publishing host.
The starter tests compare command text without spawning those commands, avoiding
recursive test execution. CI stdout retains actual counts and command results;
there is no candidate artifact export or untrusted write back to the host.

## Evidence status

**Observed:** the new test file passed a syntax-only `node --check` on the
publishing host. This does not execute the candidate module or establish runtime
acceptance. No candidate package code or guide command was executed on that host.

**Observed first-run evidence (reported by the supervising publisher):** source
`a70d14122ee0cfb4ba0164b0eb49939c771e5367`, advisory workflow run
[41801400363](https://github.com/patchwerks/furbomek/actions/runs/41801400363),
passed on both Node workers: 7 starter tests, 66 combined tests, and the documented
file-validation CLI. However, the accepted package-only workflow run
[41801400113](https://github.com/patchwerks/furbomek/actions/runs/41801400113)
failed three guide checks with `ENOENT` for `/docs/contributing/presentation-packs.md`.
Its package-only mount deliberately excludes contributor documentation.

**Correction prepared:** moved all seven contributor tests from the package test
directory to `docs/contributing/tests/presentation-packs.test.mjs`, updated imports
and guide commands, and explicitly included both test directories in the combined
command. No checks were skipped or made conditional. The accepted package-only
workflow and core tests are unchanged.

**Pending:** corrected-revision CI and its exact SHA/run IDs. The first-run passes
do not qualify this correction; no corrected runtime result is claimed.

Browser import of these starter examples was not exercised. Any previous viewer
qualification applies only to its recorded viewer revision, not this kit branch.
This kit grants no renderer, broker, Hermes, jabberWERK, OBS, installation,
deployment, hardware or live-operation authority. Parent PR 41 acceptance is
complete; this kit still requires independent review (including its workflow)
and exact-head checks before integration into main.

## Changelog

- 2026-11-04: Recorded first-run advisory passes and package-only failure; moved
  all seven contributor tests outside the package-only suite. Corrected runtime
  checks remain pending.

- 2026-11-04: Recorded parent acceptance and separate remaining kit gates; clarified
  advisory execution review and host-device exclusion. Corrected the initial
  midnight placeholder to the observed file birth timestamp in UTC. No runtime
  execution or passing test count was added.
