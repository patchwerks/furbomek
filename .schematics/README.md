# Furb-o-Mek visual schematics

These sheets are architecture, evidence-navigation, and planning aids. They are **not fabrication drawings, verified wiring diagrams, or proof that a proposed part fits**. Before hardware changes, measure dimensions, voltages, current, polarity, continuity, board revision, firmware, connector pinout, and failure behavior on the actual unit.

## Runtime boundary shown across the set

Normal autonomous operation is untethered from both the handheld movement remote and the yellow facial-control box. Neither is externally connected or authoritative at runtime. The final path is:

`offboard Linux services -> authenticated wireless link -> robot-mounted MCU/radio + isolation/driver board -> short internal motion/head links`

If a legacy head PCB is useful after characterization, it may be mounted inside the robot and driven electrically. The external buttons, knob, cable, and human control authority are removed. An independent actuator-power cutoff remains mandatory safety equipment.

## Evidence status

| Status | Meaning |
|---|---|
| Observed | Visible in repository evidence or supplied photographs |
| Measured | Recorded from this unit with method/tool/date |
| Reference / inferred | Consistent with a vendor platform or comparison source; not confirmed |
| Patent-described | Present in a cited patent embodiment; not proof of this unit |
| Proposed | Future interface or configuration; not installed |
| TBD | Requires the stated measurement or experiment |

## Sheets

| Sheet | Visual | Technical note | Scope |
|---|---|---|---|
| 01 | [PNG](./01-physical-system-blueprint.png) | [Physical system](./01-physical-system-blueprint.md) | Observed chassis/head and physical boundaries |
| 02 | [PNG](./02-onboard-control-electronics.png) | [Onboard control electronics](./02-onboard-control-electronics.md) | Controller, servo banks, WLAN/radio evidence |
| 03 | [PNG](./03-head-actuation-control-deck.png) | [Head actuation control deck](./03-head-actuation-control-deck.md) | Yellow-deck characterization and internalization |
| 04 | [PNG](./04-control-path-blueprint.png) | [Control path](./04-control-path-blueprint.md) | Untethered runtime and safety ownership |
| 05 | [SVG](./05-furby-audio-mechanism.svg) | [Furby audio and mechanism](./05-furby-audio-mechanism.md) | Patent-described 1998 architecture vs project audio proposal |
| 06 | [SVG](./06-eye-camera-integration.svg) | [Eye/camera integration](./06-eye-camera-integration.md) | Current external camera, reversible insert, long-range research |

The four existing PNGs were produced from the listed user-supplied photographs with image-generation assistance. Their labels remain planning aids; their paired notes now define the claims and stop conditions. The two SVGs are repository-native, selectable-text line art authored from cited evidence.

### 1. Physical system

[Image](./01-physical-system-blueprint.png) · [Technical note](./01-physical-system-blueprint.md)

Status: chassis, head, servos, battery bay, and legacy deck are observed; exact component identities, power topology, balance, and gateway placement remain inferred, proposed, or TBD as labeled.

### 2. Onboard control electronics

[Image](./02-onboard-control-electronics.png) · [Technical note](./02-onboard-control-electronics.md)

Status: controller, servo banks, and plug-in communication modules are observed, while MCU, WLAN/radio chipsets, protocol, and proposed robot-mounted gateway remain unconfirmed or proposed.

### 3. Head actuation control deck

[Image](./03-head-actuation-control-deck.png) · [Technical note](./03-head-actuation-control-deck.md)

Status: the legacy yellow deck is observed and limited to characterization; its external controls and cable are removed from normal runtime after a measured internal interface or replacement driver is validated.

### 4. Control path

[Image](./04-control-path-blueprint.png) · [Technical note](./04-control-path-blueprint.md)

Status: legacy control paths are reference evidence only; the untethered offboard-service-to-robot-mounted-gateway path is proposed and must pass watchdog, TTL, interlock, and loss-of-link tests.

### 5. Furby audio and mechanism

[Image](./05-furby-audio-mechanism.svg) · [Technical note](./05-furby-audio-mechanism.md)

Status: the 1998 processor/speech/DAC/speaker and motor/cam/position lanes are patent-described, actual installed electronics remain TBD, and the unified project TTS/OBS/local-playback path is proposed.

### 6. Vision integration options

[Image](./06-eye-camera-integration.svg) · [Technical note](./06-eye-camera-integration.md)

Status: the external OBS camera is the current baseline; reversible head insertion and the 1–3 mile link are proposed research gated by fit, site, link, and regulatory evidence.

## Cross-sheet safety rules

- No raw servo, GPIO, PWM, motor, shell, or OBS access is exposed to Hermes.
- The offboard gateway service is not the robot-mounted isolated microcontroller gateway.
- Robot-side TTL, watchdog, sequence checks, mutually exclusive head directions, and unconditional `STOP` survive offboard failure.
- Video loss never authorizes continued motion and is never the stop mechanism by itself.
- Speaker reuse, camera fit, long-range RF, and exact controller identities remain TBD until measured.

## Source photographs for the existing PNGs

- Sheet 01: `IMG_5171.jpeg`, `IMG_5174.jpeg`, `IMG_5175.jpeg`
- Sheet 02: `IMG_5179.jpeg`, `IMG_5180.jpeg`, `IMG_5187.jpeg`
- Sheet 03: `IMG_5527.jpeg`, `IMG_5529.jpeg`, `IMG_5543.jpeg`
- Sheet 04: `IMG_5531.jpeg`, `IMG_5533.jpeg`, `IMG_5538.jpeg`, `IMG_5174.jpeg`

The original photographs are not committed here.

## Generation provenance

The existing four PNG sheets were generated from the listed user-supplied photographs using OpenAI image generation and remain planning aids rather than verified fabrication or wiring drawings. The new sheet 05 and 06 SVGs are repository-native vector evidence/design sheets authored from the cited patent, vendor, standards, and technical sources. The original photographs are not committed, and this index contains no personal information.
