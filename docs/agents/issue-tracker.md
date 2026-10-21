# Shared issue tracker

## Authority and access

- Work records: [patchwerks/furbomek Issues](https://github.com/patchwerks/furbomek/issues).
- Shared board: [Furb-o-Mek delivery](https://github.com/orgs/patchwerks/projects/1).
- Views: [All work](https://github.com/orgs/patchwerks/projects/1/views/1),
  [Software](https://github.com/orgs/patchwerks/projects/1/views/2),
  [Physical gates](https://github.com/orgs/patchwerks/projects/1/views/3), and
  [Ready to claim](https://github.com/orgs/patchwerks/projects/1/views/4).

This is a private organization Project linked to the private repository. Existing
repository collaborators were granted corresponding Project reader/writer access,
without making the board public or elevating their roles. Repository access and
Project access are separate: maintainers must reconcile both when membership changes.
Never make either public merely to let an unauthenticated browser see it.

GitHub owns issue identity, claims, dependencies, acceptance and closure. Hermes
kanban, OmO Tasks, Claude/Codex todos and other harness queues may track execution
subtasks, but must carry the canonical issue URL and report progress back here.
There is no automatic cross-harness synchronization or atomic checkout lock.
Do not create a competing source of truth or synchronize private transcripts.

[PLAN.md](../../PLAN.md) remains architecture/roadmap authority. An issue schedules
a bounded slice; it cannot silently override the plan or safety gates. See
[domain routing](domain.md) and [triage labels](triage-labels.md).

## Workflow

| Status | Meaning |
|---|---|
| Backlog | Intake or work not yet selected/sufficiently specified |
| Ready | Specified, unblocked and available to claim |
| In progress | One current owner has posted an explicit claim |
| Review | Implementation/evidence ready for independent acceptance |
| Blocked | Named dependency, access, decision or physical gate unresolved |
| Done | Accepted, published and closed; not merely code written |

Use native GitHub issue dependencies plus a readable **Blocked by** section.
The initial software dependency chain is #2 -> #6; #3, #5 and #6 -> #7; #7 -> #8.
#4 is independent verification work. #9 and #10 are separate physical gates,
not prerequisites for software work. This is a seed map, not a status mirror:
the live issues and Project carry current state.

GitHub's built-in item-closed and PR-merged workflows are enabled. The default
Auto-close issue workflow is also enabled: moving a card to Done can close it.
Never move to Done to bypass review. A linked PR closing keyword only closes its
issue when merged into the repository's default branch. There is no promise that
closing a blocker automatically updates downstream labels/status; the completing
agent must re-evaluate dependencies and promote newly ready work explicitly.

## Find and claim work

Use `gh` with explicit repository/owner; another harness's working directory must
not redirect the operation. Commands below were checked with GitHub CLI 2.82.0.

```sh
gh project item-list 1 --owner patchwerks --limit 100 --format json \
  --jq '.items[] | select(.status == "Ready") | {number: .content.number, title}'
gh issue view 2 --repo patchwerks/furbomek --comments
```

Before editing or using shared resources:

1. Read the issue, comments, native dependencies, relevant plan and scoped guides.
   Ready status alone is not enough if a later comment records a blocker.
2. Check for an existing live claim. Assign yourself where permitted, move the
   item to In progress, and post this claim record:

   ```text
   CLAIM
   Owner: human/agent identity and GitHub account
   Harness/session: harness name and session identifier, if available
   Branch/worktree: issue-numbered branch and separate worktree identifier
   Scope: owned components and explicit exclusions
   Shared resources: none, or the separately agreed operator/resource window
   Next checkpoint: expected next update or exact blocker
   ```

3. Fetch published main from the configured repository remote and use an isolated
   branch/worktree, conventionally `work/<issue-number>-<short-description>`.
   Existing workspaces use `upstream/main`; fresh clones may call that remote
   `origin`. Do not switch a shared main checkout or discard another agent's work.
4. Recheck recent claims for races. An assignee is not a lock, especially when
   several harnesses share a GitHub account. Resolve conflicting claims before
   working; do not silently steal a claim based on an invented timeout.

Humans and read-only collaborators can comment, but may need a maintainer to
apply assignments/Project transitions. No permission failure justifies broadening
access or ignoring another owner. On handoff, post progress, commits, evidence,
remaining work and whether the claim/resources are released. Release or explicitly
hand off the claim before closing the agent session.

## Create, block and promote issues

Use the repository's software-slice or physical-gate issue forms. Each issue needs
an independently verifiable outcome, acceptance criteria, non-goals, dependencies,
verification surface and evidence requirements. Apply the triage vocabulary rather
than inventing per-harness status labels.

Forms request Project `patchwerks/1`; GitHub may require Project write permission
to honor that request. CLI-created issues and any missed form additions must be
added explicitly; generic repository-wide auto-add was not configured:

```sh
gh project item-add 1 --owner patchwerks \
  --url https://github.com/patchwerks/furbomek/issues/2
gh project field-list 1 --owner patchwerks --format json
```

For CLI status updates, discover the item ID from `item-list` and Status field /
option IDs from `field-list`, then use the installed CLI's `gh project item-edit
--id ITEM_ID --project-id PROJECT_ID --field-id STATUS_FIELD_ID
--single-select-option-id OPTION_ID`. Do not assume newer name-based flags exist.

Only unblocked issues receive `ready-for-agent` and Ready status. When blocked,
remove `ready-for-agent`, add `blocked`, set Blocked, and comment with the precise
missing prerequisite and next action. Add `needs-info` for missing information or
`ready-for-human` for a human decision/physical step. On promotion, verify the
dependency's accepted evidence, clear resolved blocker labels and update both
Project status and triage role. Board changes do not automatically synchronize labels.

`requires-hardware` always invokes physical safety/ownership gates regardless of
card position. Creating, assigning or moving an issue never authorizes probing,
serial access, USB reset, flashing, energization or movement. Claims do not isolate
camera, OBS, Hermes profiles, audio, USB/RF or power. Only the designated operator
may own shared live resources; keep all other agents non-live.

## Review and closeout

1. Update the issue's acceptance checklist with actual evidence, not predictions.
2. Run relevant locked tests/types/builds and use the matching real surface.
   Distinguish non-live fixtures, private acceptance and physical qualification.
3. Record exact revisions/artifact hashes, results, limitations and rollback in
   the appropriate operations/hardware records. Never attach credentials, raw
   transcripts, private voice assets, camera recordings or device identifiers.
4. Open a reviewed PR targeting main with `Closes #N`. Put the card in Review;
   publish independent review and qualification evidence before merging. A green
   build is not a substitute for acceptance, and software tests do not install firmware.
5. After merge, verify the published revision, issue closure and Done status.
   Record any remaining blockers separately, re-evaluate dependent issues, release
   claims/resources and leave the owning worktree clean. For an explicitly
   authorized non-code investigation, close with evidence and reason instead of
   manufacturing a code PR. Closing as not planned must explain why; it is not
   acceptance completion.

## Official references

- [GitHub Projects automation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations).
- [PR closing keywords](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
- [GitHub CLI project manual](https://cli.github.com/manual/gh_project).
