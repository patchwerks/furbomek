# Citation and editorial code review

- Scope: `linux-live-visuals-touchdesigner-alternatives-2026-10-01.md`, full untracked document (190 lines at review).
- Goal: verify citation integrity, local links, consistency, price arithmetic, Markdown structure, privacy, and coverage of the research brief.
- codeQualityStatus: WATCH
- recommendation: APPROVE
- blockers: none within this bounded editorial review; this does not certify hardware, visual parity, all external claims, or other review lanes.
- Report placement: `omo-agent-toolkit ulw-loop status --json` returned `ULW_LOOP_PLAN_MISSING`; fallback path used.
- Inputs: team guide, `.omo/ulw-research/20261001-083328/brief.md`, tracking and visual-acceptance evidence notes, and the entire target document. No separate notepad path was supplied. Source SHA matches repository HEAD `98fd3d2b1679200ca589c4d5fa11c758166f64bd`.

## CRITICAL

None found.

## HIGH

None found.

## MEDIUM

- Line 120: “gives the exact flat sampled look” is more confident than the document's explicit lack of an exact-match recording (lines 12 and 105). Change to “can approximate the sampled look; compare a rendered recording for fidelity.” Forwarded to the visual reviewer for independent assessment.

## LOW

- Line 2: unresolved `STATUS: draft — source verification and proofread in progress`. Resolve the marker when source review finishes before final publication.
- Line 120: the citation labeled “relative output and license matrix” points to README lines 33–42, which contain model sizes and download links. The license terms are at lines 178–180. Link both sections or correct the label and add the license anchor.
- Line 188: “two additional used offers” points to only one Mercari item. Add the second item URL already cited at line 44, or use a singular label.

## Verified evidence

- All eight distinct local/anchor targets exist, including `#v1`.
- Four Markdown tables have consistent 3/6/4/2-column widths; the Mermaid code fence is balanced. Diagram syntax was inspected; no rendered diagram QA was performed in this lane.
- Price arithmetic: $29.99 + $7.97 + $1.36 = $39.32.
- All 43 distinct pinned GitHub blob citations fetched successfully using their raw equivalents; referenced line ranges exist. This verifies accessibility/ranges, not every semantic claim.
- Godot 4.7 CameraServer documentation explicitly lists Linux support: https://docs.godotengine.org/en/4.7/classes/class_cameraserver.html .
- The Microsoft hand-shape paper supports Kinect V2 time-of-flight, discontinuity noise and multipath claims in section 5.1, page 7: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/HandShapeVariation.pdf .
- Depth Anything source at pinned SHA supports relative output at lines 33–42 and the model-specific licensing at 178–180: https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/README.md .
- Basic private-path, credential/token, email and unresolved-marker scan found only the draft STATUS marker. Human reading found no obvious private information.
- The supplied brief's five-candidate ranking, two camera classes, effects matrix, integration, and deployment gates are present. The original user conversation was unavailable to this lane, so completeness is evaluated against that brief.

## Skill-perspective check

Loaded and consulted `omo:remove-ai-slops` and `omo:programming`, especially their prose-test exemption, behavior-over-constant testing, boundary validation, and minimal-complexity principles. No production code or tests are changed in this review scope. No deletion-only tests, prompt tests, implementation-mirroring tests, untyped escape hatches, or unnecessary production parsing/normalization exist in the scoped change. Neither perspective is violated. No wording-pinning tests were added.

## Limits

This is a documentation-only review. Camera prices/stock, software compatibility, full source semantics, video content and architecture are owned by the parallel specialist lanes; this report does not certify their conclusions. No Linux runtime or physical device was tested. This reviewer modified no implementation or research-document content; only this required review artifact was written.

## EXPAND

No broad research expansion is needed for editorial QA. Correct the exactness wording and citation labels, resolve the draft marker after the specialist reviews, and render the Mermaid diagram in the final handoff surface.
