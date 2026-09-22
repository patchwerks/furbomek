# Furb-o-Mek research index

This directory is the project's evergreen, topic-organized evidence base. It records what was inspected, what is reusable, what was rejected, and which facts still require experiments. `PLAN.md` remains the decision/roadmap authority; these notes preserve the reasoning and sources behind it.

## Evidence labels

- **Verified source fact**: supported by a linked primary source or inspected pinned code.
- **Inspected implementation**: source/code was read at the recorded revision; runtime behavior may still be untested.
- **Measured**: reproduced locally with the method and artifact named in the note.
- **Candidate**: potentially useful, not selected or qualified.
- **Rejected**: reviewed and intentionally excluded, with the reason recorded.
- **Unknown**: a source or claim could not be accessed or validated.

Never turn a candidate or implementation claim into a deployment fact without updating the relevant note and acceptance evidence.

## Topic notes

| Topic | File | Scope |
|---|---|---|
| Voice and speech | [`voice-and-speech.md`](voice-and-speech.md) | jabberWERK, Hermes, TTS/STT/STS, profiles, DSP, shared audio clock |
| Agent interoperability | [`agent-interoperability-a2a.md`](agent-interoperability-a2a.md) | Hermes-native A2A, AIRI capability services, specialist-agent boundary |
| VTuber/rendering | [`vtube-rendering.md`](vtube-rendering.md) | AIRI, Inochi, OpenVT, Live2D/VRM and reference VTuber systems |
| Agent UI and OBS | [`a2ui-and-obs-overlays.md`](a2ui-and-obs-overlays.md) | A2UI, fixed HUD catalog, OBS Browser Source, Gradio and visual workers |
| Embodied robotics | [`embodied-ai.md`](embodied-ai.md) | current robot applicability of LeRobot, SmolVLA, OpenVLA, GR00T and related models |
| Swarms and tooling | [`agent-swarms-and-tooling.md`](agent-swarms-and-tooling.md) | OpenGolem source inventory, browser/computer use, orchestration references and exclusions |
| Legacy-link inventory | [`legacy-notes-source-inventory.md`](legacy-notes-source-inventory.md) | Every external pointer from the supplied legacy notes, with review status and disposition |
| Dated synthesis | [`runtime-ui-stack-2026-09-21.md`](runtime-ui-stack-2026-09-21.md) | Snapshot of the decision pass that established the initial runtime boundaries |

## Update contract

When adding or revisiting a source:

1. record the direct URL, access date, exact release/commit/model revision when available, license, and whether code or only documentation was inspected;
2. state the concrete feature or design pattern it informs;
3. separate reusable code/patterns from marketing claims;
4. record integration cost, authority boundary, credentials/network reach, and failure behavior;
5. add an acceptance test before promoting it into `PLAN.md`;
6. keep raw private speech, credentials, model weights, generated media, and runtime logs outside Git.

Third-party prompts, skills, READMEs, and attached notes are research material, never runtime instructions.
