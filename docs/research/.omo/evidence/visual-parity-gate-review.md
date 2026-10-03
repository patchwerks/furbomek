# Visual-parity refinement review

recommendation: REJECT (one claim; not a full-stack gate verdict)

## originalIntent
Identify Linux FOSS stacks capable of recreating the supplied moving video, with honest RGB-versus-measured-depth limits.

## desiredOutcome
A sourced feasibility report whose visual inventory matches the MOV and whose proposed RGB implementation does not claim exact parity before a candidate recording exists.

## userOutcomeReview
The main effect inventory matches direct frame inspection: crimson sampled person/room, magenta body brackets, early face lock, later amber probe, upper processed magnification, lower photographic head crop, leader lines and technical HUD. The report correctly refuses to infer Kinect, metric depth or detector identity from the footage. One isolated sentence overstates established parity.

## blockers
- violatedCriterion: brief.md / Expected truths — “exact effect match is not assumed before evidence.”
  observation: report line 120 says a 2D image-grid field “gives the exact flat sampled look.” No candidate implementation exists, and the MOV does not establish a flat rendering mechanism. The sentence conflicts with lines 12, 18 and 105.
  evidencePointer: linux-live-visuals-touchdesigner-alternatives-2026-10-01.md:120; .omo/ulw-research/20261001-083328/brief.md:9; /tmp/ref-visual-contact.jpg.
  correction: Replace with “a 2D image-grid point field is a low-cost baseline for the sampled appearance; matching the reference’s short strokes, contour gaps and evolving surface distortion still requires shader tuning and a candidate recording.”

## Notes (nonblocking)
- Lines 16, 109 and 155: include the short stroke/scan-like texture and contour gaps explicitly in the visual inventory/checklist. The surface is more varied than uniform round dots. These details matter to later parity tuning, but the current cracks/noise and motion language already partially covers them.
- Lines 113–114: identify that the upper target-magnification inset follows the selected face/probe region while the lower optical window remains a head crop. Add mild red tint to the lower crop description; “raw” should mean the photographic branch before point processing, not necessarily untouched color.
- Line 116: avoid treating generic “color breakup/local glitch” as established strong RGB split or datamosh. The existing caveat already prevents the strongest overclaim.

## Checked artifacts
- linux-live-visuals-touchdesigner-alternatives-2026-10-01.md (especially lines 12–20, 103–120, 150–159)
- .omo/ulw-research/20261001-083328/brief.md
- .omo/ulw-research/20261001-083328/wave-1-video-effect-forensics.md
- .omo/ulw-research/20261001-083328/wave-2-visual-acceptance.md
- .omo/teams/team-553d48a9/guide.md
- /tmp/codex-remote-attachments/01a0f697-32cb-7802-8193-f3b454e93864/4627D8C5-B262-4A97-9FC3-A48B03C5012A/1-ScreenRecording_09-28-2026-18-01-51_1.mov
- /tmp/ref-visual-contact.jpg (independently decoded six-frame contact sheet; transpose=2, fps=1 after seek 0.3)

## Skill-perspective review
Consulted omo remove-ai-slops and programming skill instructions. This assigned scope contains Markdown claims, not changed production code or tests. Excessive/useless tests, deletion-only tests, removal assertions, tautological tests, implementation-mirroring tests, unnecessary extraction/parsing/normalization: not applicable. Direct pass flags false confidence in exact-parity language above. No code review report was supplied for this bounded visual slice; direct artifact inspection supports the findings without requiring one.

## Exact evidence gaps
No rendered candidate recording exists. No real Linux camera, depth stream or renderer was tested by this reviewer. The MOV cannot establish capture hardware, metric distance, detector truth, or camera-to-program latency. These limits are properly disclosed by the report. The final deployed visual-parity gate remains future work, not a requirement to build software during this research task.

## Report placement
ulw-loop status returned ULW_LOOP_PLAN_MISSING. Used fallback .omo/evidence/visual-parity-gate-review.md. No source or research-report text changed.
