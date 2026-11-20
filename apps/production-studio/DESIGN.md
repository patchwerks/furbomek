---
created: 2026-11-20T00:00:00Z
branch: codex/production-wave-03-task-15
author: patchWERKS / Codex
status: active
---
# Production studio design

## 1. Purpose
Private owner authoring. Primary action: preview a bounded effect before applying it to the fixture. Priorities: mode and readiness, effective state and revision, reversible editing. No runtime admission is implied.

## 2. Sources and tokens
The existing [Godot design](../../tools/kinect2/godot/DESIGN.md) supplies the crimson family, quiet surfaces and data provenance. The bundled Ioskeley Mono font is reused by source import, including its existing OFL notice. Native form and button anatomy follow the sibling extension viewer; no new component framework.
Dark: page #100d10, surface #1b161a, ink #f2e7eb, muted #c5adb7, border #86717b, accent #f591a4, selected #35232b. Light: page #faf7f8, surface #ffffff, ink #281820, muted #68515c, border #967d89, accent #8b2944, selected #f4e5eb. Status ink uses the theme accent and explicit words, never color alone. Preview signal colors: #ef476f, #63c892, #689ee8; they are labelled synthetic RGB bars, never a camera image.

## 3. Typography
Ioskeley Mono for project identity, identifiers and data; system sans-serif for readable controls and body. Size roles: small 12px, body 14px, h3 18px, h2 24px, h1 30px. Line height 1.5. No decorative motion.

## 4. Spacing and layout
Base 4px; steps 8,12,16,24,32,48. Radius 4px. Control minimum 44px, wrap actions with 8px gaps. Neutral 1px rules, no shadows.
Layout: effects workspace - inspect a catalog beside a selected effect -> list-detail; scroll owner: document; anti-patterns: nested scroll traps, fixed heights that clip controls, source order different from keyboard order. On narrow widths stack detail after inventory, with inventory in a disclosure. Reaction and framing pages use a single reading column and wrapping editor rows. Navigation and status remain in document flow.

## 5. Primitives
Button: native button, hover tonal, pressed tonal, 2px focus ring, disabled explicit. Field: native labelled input/select, bounded values and adjacent instructions. Inventory row: selected tonal background and aria-pressed. Status: semantic text, not decorative badges. Preview: fixed 16:9 frame, synthetic or unavailable states. Timeline: ordered semantic list with completion dependencies. These primitives also appear in the fixture scenario controls for stale, blocked and disconnected states.

## 6. Required content
Fixture/live separation; origin, owner, epoch and applied revision; hardware/derived/renderer catalog; fixed RGB fixture; ranges; preview/apply/revert/save/restore; reaction sequence/parallel editor; preset binding; semantic validation and cancellation; framing anchor and ordered rules; readiness and network recovery.

## 7. Recovery
Dirty draft survives polling and reconnect; a new server epoch or revision invalidates preview. Revert is explicit and creates a new revision. Saved state never auto-applies. Network failures clear preview and disable writes. Live API mode remains unavailable until Task 14/16 acceptance.

## 8. Accessibility
Both themes, visible focus, no drag-only editing, 44px controls, semantic landmarks and labels, live action feedback, reflow at 320px. No audio or animation. Evidence is recorded outside this app; no unsupported blanket conformance claim.

## 9. Grounding ledger
New surface: no before capture exists. Review must inspect default/effect, reaction, framing, stale and disconnected states, with end-of-page captures and light/dark reflow. No stock media, decorative charts, metrics or fake live views.
