# Embodied AI and robotics references

Reviewed: 2026-09-21

## Current applicability

The current Furb-o-Mek is a modified 18-servo hexapod with a coupled Furby-like head, not a supported 7-DoF manipulation arm or humanoid embodiment. None of the referenced VLA/foundation models is a drop-in gait or face controller.

Near-term architecture remains:

```text
Hermes semantic intent
→ deterministic embodiment policy
→ bounded named pose/gait/face command
→ robot-mounted MCU watchdog/interlocks
→ existing calibrated mechanisms
```

Learned policies may eventually propose higher-level motion, but they cannot replace the robot-local safety plane.

## Source inventory

| Source | What it provides | Relevance now |
|---|---|---|
| [Reachy Mini](https://pollen-robotics-reachy-mini.hf.space/getting-started) | Open companion-robot product/reference with perception, speech and expressive embodiment | Strong product/UX reference for future desktop agents; do not infer hardware compatibility |
| [Adafruit Furby 2012 teardown](https://learn.adafruit.com/furby-2012-teardown) | Generation-specific disassembly/navigation evidence | Mechanical/electrical comparison only; the installed Furby generation remains unconfirmed |
| [HY-Embodied-0.5](https://huggingface.co/tencent/HY-Embodied-0.5) | Embodied multimodal model research | Research pointer; inspect action space/hardware/compute before any experiment |
| [Utonia](https://huggingface.co/Pointcept/Utonia) | Spatial/3D feature research intended to improve VLA policies and spatial reasoning | Perception/representation research, not current actuation |
| [OpenVLA 7B](https://huggingface.co/openvla/openvla-7b) | Image + language to normalized 7-DoF end-effector deltas; MIT code/model claims | Not compatible with unseen hexapod embodiment without data/adaptation; model card explicitly warns against unseen zero-shot embodiments |
| [GR00T N1.7 3B](https://huggingface.co/nvidia/GR00T-N1.7-3B) | Cross-embodiment humanoid manipulation model using vision, language, proprioception and embodiment ID | Future advanced-robot reference; current robot lacks its action/state contract and suitable training data |
| [SmolVLA base](https://huggingface.co/lerobot/smolvla_base) | Compact VLA aimed at affordable robotics | Best-sized VLA research candidate, still requires a compatible observation/action schema and demonstrations |
| [SmolVLA paper](https://arxiv.org/abs/2506.01844) | Architecture/evaluation evidence for the compact model | Research/design reference |
| [LeRobot](https://github.com/huggingface/lerobot) | Dataset, model, training/evaluation and robot integration ecosystem | Useful future data/interface standard; not a substitute for current safety firmware |

## Why these models are not immediate movement controllers

- OpenVLA outputs a specific normalized manipulation action representation and requires per-robot statistics; its model card says unseen embodiments require demonstrations/fine-tuning.
- GR00T requires camera, proprioceptive and embodiment-specific state/action tensors and is optimized for substantially different robots/hardware.
- The current Furb-o-Mek repo has no calibrated observation/action dataset, URDF/digital twin, servo telemetry contract, demonstration recorder or safe learned-policy adapter.
- Hexapod gait timing and coupled face motion must first be restored and bounded deterministically.

Consequently, a VLA cannot send raw servo angles. A future adapter may emit only the same named, bounded semantic actions available to Hermes, with policy validation and local TTL/watchdog unchanged.

## Compounding path toward replaceable desktop embodiments

1. Define robot-neutral state and named-action contracts.
2. Build a simulator and hardware adapter that pass identical safety tests.
3. Record timestamped observations, accepted commands and outcomes without private stream content.
4. Add proprioception/current/contact/position sensing where mechanically justified.
5. Create an embodiment descriptor and reversible dataset recorder.
6. Evaluate LeRobot-compatible storage/training interfaces.
7. Train/evaluate learned proposals in simulation and supported-bench mode.
8. Permit only policy-approved named actions on hardware; never raw learned actuation.
9. When replacing the robot, implement the same embodiment contract plus capability manifest.

## NVIDIA/GR00T note

The live NVIDIA skills catalog contains Physical AI/robotics and GR00T dataset/workflow material, but no specific installed skill was identified as necessary for this planning-only pass. If the project reaches GR00T/Isaac simulation or fine-tuning, re-run the catalog and use the matching NVIDIA-verified workflow rather than inventing install/training steps.

GR00T N1.7's published examples and performance use high-end NVIDIA hardware and task-specific embodiments. The Omen GPU has not been inventoried in this repository; no GR00T capacity claim is made.

## Acceptance gate for any learned policy

- exact model/code/data license and revisions recorded;
- target observation/action schema documented;
- training/demo data provenance and coverage recorded;
- offline/simulation benchmark against deterministic baseline;
- adversarial/stale/out-of-range outputs rejected;
- no raw actuator path from model to hardware;
- local watchdog/interlocks/STOP remain authoritative;
- hardware test uses support rig and independent actuator cutoff;
- rollback to deterministic control is immediate and proven.

## Unavailable sources

The Reachy YouTube link and the supplied X post were not retrievable through the available web reader. They remain pointers only and are not used as technical evidence.
