---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-08-task-25
author: patchWERKS / Codex
status: active
---
# Advanced owner editor fixture

Run the studio's local Vite server and open `/fixture/live-editors/index.html`.
This isolated entrypoint mounts the real advanced editors without an HTTP owner
controller. It records emitted events as synthetic component evidence. It never
opens a camera, dispatches to a renderer, or changes live settings.

Both components consume the Task24-generated `liveGenerated.ts` contracts:
`modelValue`, required `disabled`, optional `canApply` (defaults false),
`unavailableReason` and `currentReason`. Apply and manual hold additionally require
`canApply`; a dispatch HOLD may leave editing, preview and save available.
They publish valid draft changes through `update:modelValue` and request `preview`
or `apply` without a payload. Framing additionally requests `save` and emits a
canonical `Manual` payload through `manual`. Visual settings have no save action.
The parent owns authentication, revisions, observed state and every dispatch.

Invalid field input remains visible locally and blocks editor actions. The
framing editor checks crop containment and referential consistency for immediate
feedback; the Python controller remains the semantic authority. Changing the
parent model replaces the local draft; parent polling must preserve dirty drafts.
An unavailable reason or disabled state holds all controls. Default factories in
`liveDefaults.ts` create authoring values only, never observed or ready state.

Layout: advanced editor forms - inspect and edit grouped settings -> single
reading column with wrapping field grid, matching the studio DESIGN.md; scroll
owner: document; anti-patterns: nested scroll regions and clipped fixed heights.
Primary action: Apply within each independent editor. Priorities: current reason,
configuration, explicit action. No raw JSON editor, preview image, or readiness
claim is supplied by these components. Ioskeley is inherited for numeric hints;
all visual tokens and native control states come from the studio stylesheet.
