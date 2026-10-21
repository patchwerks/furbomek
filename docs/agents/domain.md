# Domain documentation routing

There is currently no `CONTEXT.md`, `CONTEXT-MAP.md` or `docs/adr/` tree. Do not
invent a second domain model or claim those files exist to satisfy a skill.

Use the existing authority and evidence layout:

1. [Root agent guide](../../AGENTS.md): scope, architecture boundaries and safety.
2. [PLAN](../../PLAN.md): domain terminology, selected architecture, milestones,
   constraints, acceptance gates and immediate execution order.
3. [Research index](../research/README.md) and the issue-relevant topic notes:
   source evidence and proposed versus qualified capabilities, not plan overrides.
4. [Operations](../operations/AGENTS.md) and relevant dated records: actual
   deployment, commands, hashes, verification, recovery and rollback limits.
5. [Hardware records](../hardware/README.md) and scoped firmware/gateway guides
   before any physical work; source-only candidates are not installed firmware.

Hermes is the sole planning/tool authority. jabberWERK is the speech/media plane.
The character broker owns presentation state; renderers are unprivileged adapters.
Head-controller identity/USB capability, physical interlocks and full autonomy
remain separate gates. Public desktop screenshots remain blocked.

An issue may refine a bounded implementation, not silently replace these
decisions. Update the appropriate existing authority with evidence when a real
decision changes; introduce an ADR/context layout only as an explicitly scoped
future change.
