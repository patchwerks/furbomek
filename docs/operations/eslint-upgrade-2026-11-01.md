---
created: 2026-10-31T20:58:46Z
branch: codex/30-eslint-upgrade
author: Codex
status: active
---
# ESLint 30 qualification candidate

Tracks [issue 30](https://github.com/patchwerks/furbomek/issues/30), based on
`fb7e25e9982f53a1f12e6c63955420ac476d8294`. This is preparation, not accepted
qualification. The candidate lockfile has not yet been generated in the required
Linux worker. Application source and the generated-config wrapper are unchanged.

## Observed metadata and proposed versions

Official npm metadata inspected on 2026-11-01 selects `@nuxt/eslint` 1.17.0 and
ESLint 10.14.0. The [ESLint support table](https://eslint.org/version-support/)
marks 9.x EOL since 2026-08-06; selecting 9 would not satisfy maintained-runtime
acceptance. The root explicitly selects ESLint 10.14.0 instead of relying on a
transitive peer installation.

The [Nuxt module metadata](https://registry.npmjs.org/@nuxt%2feslint/1.17.0)
requires inspector ^3.2.0 and accepts ESLint ^9 or ^10. Existing inspector
[1.3.0 metadata](https://registry.npmjs.org/@eslint%2fconfig-inspector/1.3.0)
accepts only ESLint ^8.50 or ^9. Keeping it together with one maintained ESLint
major is therefore incompatible without prohibited peer overrides.
[Inspector 3.2.0](https://registry.npmjs.org/@eslint%2fconfig-inspector/3.2.0)
is an explicit candidate dependency, not a qualified replacement yet. Its direct
dependencies no longer include esbuild or bundle-require; the resolved transitive
paths and audit must still be examined. No override or rule suppression is added.

## Proposed advisory Linux evidence

The branch-push/manual `eslint30-qualification.yml` workflow compares fixed
baseline source with the exact workflow head. It is advisory and does not activate
or modify the issue 4 trusted worker or dispatcher. It uses the accepted immutable
Node 26.7.0/Python images and proxy from the fixed baseline. Source snapshots omit
Git state; tracked symlinks, gitlinks, npm configuration and environment files
are rejected before staging. Networked unprivileged workers
only resolve/install dependencies with lifecycle scripts disabled through the
registry allowlist. Fresh network-none workers execute Nuxt preparation, production
build/type checks, vue-tsc, offline full npm ci, effective-config inspection,
malformed Vue/TypeScript parsing and lint diagnostics. The existing lint debt
remains visible as exit 1; fatal/configuration failures are failures.

The evidence records full lock, audit and dependency paths, including inspector,
esbuild, glob and minimatch; effective Vue/TypeScript rule differences must be
reviewed before claiming no weakening. A newer preset can change severity or
remove rules without editing the wrapper, so unchanged wrapper text alone is
insufficient evidence.

## Open gates and rollback

Shell syntax and whitespace checks passed. No baseline or candidate execution
checks have run in this preparation. Historical counts
are inconsistent: the issue records app 11 errors/18 warnings and repository
33 errors/23 warnings, while the existing compatibility note records repository
31 errors/23 warnings. The workflow must derive both counts. Existing lint debt
means clean-lint acceptance remains unmet unless separately resolved; this change
must not hide it through application edits or disabled rules.

Node 26.7.0 qualifies only that supported version, not the declared 22.22.3 floor.
Dependency engine compatibility and runtime verification at the floor remain open.
Independent review, exact-head checks, inspector replacement qualification and
resolved lock generation remain required. Reverting the manifest and matching
lock restores the former toolchain, including its documented unsupported ESLint
8 runtime. No deployment, provider call, device or live service is involved.
