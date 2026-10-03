# Wave 1: project architecture

Observer: repo_plan. Read PLAN.md, HERMES.md, docs/research and operations entrypoint.

Observed/planned distinction: PLAN.md calls for Hermes -> adapter -> character broker -> isolated renderer, separate stream director owning authenticated OBS, optional reduced A2UI/Lit HUD, timestamped perception boxes/masks and lower inference cadence. Events may select reviewed preset IDs and bounded duration, not submit arbitrary shaders/code/asset URLs. Internal renderer shaders are consistent with that boundary. OBS continues on Hermes restart; static fallback and snapshot recovery require proof. 1080p30 is a program-output planning baseline, not measured performance. 10 HUD deltas/s applies to semantic events, not rendering FPS. 720p30 line at PLAN.md:500 and 1080p30 at :612 require an explicit phase/profile interpretation; ≤2-second production fallback at :616 differs from tonight's ≤2-minute tracer bullet at :856.

EXPAND: define bounded effects contract; benchmark capture path copies/alpha/latency/recovery; preserve current Linux first and defer Omarchy qualification; separate phase-specific resolution/fallback gates.
