# Triage vocabulary

GitHub Issues are authoritative; Project status and labels are separate fields.
Apply this vocabulary from every harness, including the engineering skills.

| Canonical role | Repository label | Meaning |
|---|---|---|
| needs-triage | `needs-triage` | Scope, acceptance or readiness needs evaluation |
| needs-info | `needs-info` | Waiting for named information/access |
| ready-for-agent | `ready-for-agent` | Specified, unblocked and available for an agent |
| ready-for-human | `ready-for-human` | Requires a human decision or physical action |
| wontfix | `wontfix` | Will not be actioned; record a reason before closure |

Additional configured labels:

- `blocked`: unresolved prerequisite; Project status must be Blocked.
- `requires-hardware`: physical ownership and safety gates apply, regardless of
  board status; never an authorization to access a device.
- Areas: `area:character`, `area:speech`, `area:avatar`, `area:verification`,
  `area:robot`, `area:head`, `area:workflow`.
- Preserve existing GitHub labels such as `bug`, `enhancement` and `documentation`.

Do not add `ready-for-agent` to dependency-blocked or physical-gated work.
Blocked work may have no readiness role until its prerequisites are resolved;
physical work normally combines `blocked`, `ready-for-human` and
`requires-hardware`. Missing credentials/asset permissions are blockers, not
permission to select a substitute provider or publish private data.

On claim, keep the applicable readiness role for its specification provenance
but move the card to In progress; dispatch must check both status and claims.
On release, return to Ready only if still unblocked, otherwise Blocked. On closure,
remove active readiness/blocker labels that no longer apply. Record cancellation
or not-planned disposition honestly rather than presenting it as delivered work.

See [tracker policy](issue-tracker.md) for claim, dependency and closeout details.
