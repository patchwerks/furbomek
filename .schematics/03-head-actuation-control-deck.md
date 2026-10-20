# Sheet 03 — Head actuation control deck

Companion image: [03-head-actuation-control-deck.png](./03-head-actuation-control-deck.png)

## Purpose

Document the observed yellow deck as an object to characterize and retire from external runtime, not as a human interface the finished robot requires.

## Observed and inferred elements

The photographs show red/green momentary controls, a speed potentiometer, a reversible PWM motor-control board, two `SRD-05VDC-SL-C` relays, and a cable to a coupled head mechanism. These observations do not establish button voltage, polarity, logic topology, shared ground, relay contacts, motor voltage/current, potentiometer taper, or safe travel.

The original-era Furby patent family describes a reversible motor and cam/gear train coordinating multiple facial/body motions, with position sensing in the cited embodiment. The installed generation and presence of its original sensor remain TBD ([US6149490A](https://patents.google.com/patent/US6149490A/en), [US6497607B1](https://patents.google.com/patent/US6497607B1/en)).

## Characterize, then internalize or replace

### Separate host bridge inspection, 2026-10-19

The user plans to inspect the separate head-control device for a possible USB
link to Brodex while preparing eventual internal wiring. This is not the Freenove
chassis handheld whose USB/RF bridge is already verified. The documented head
device is the yellow wired deck above; if another controller is present, identify
it separately. USB data capability and a host protocol are **unknown**, not absent
and not established by a connector's shape. No head probe or movement occurred.

Only after motor-power isolation and device identification should an agent inspect
enumeration/protocol non-destructively. Do not apply chassis firmware or assumed
GPIO voltage to the head device. A temporary verified bridge is a bench integration
step, not a revision of the final untethered/internalized runtime plan. Bounded
pulses, mutually exclusive directions, local STOP/expiry and measured electrical
compatibility remain required before Hermes head actuation.

1. Remove power and photograph every board face, connector, wire color, motor label, and control marking.
2. With current-limited power, record button-released/pressed voltages relative to every plausible reference; then map continuity unpowered.
3. Measure output polarity, PWM/frequency, speed range, no-load and stall current, relay truth table, and both-buttons behavior.
4. Identify any home/limit/Hall/optical/encoder signal and its full-cycle waveform.
5. If input topology, reference, voltage, or polarity is unknown, make no connection.
6. After measuring, default to an optocoupler, PhotoMOS, or dry-contact relay rated for the measured signal.
7. An open-drain or transistor output is permitted only after a compatible shared reference and voltage/current levels are confirmed.
8. Choose one measured path: retain the useful PCB entirely inside the robot and drive it through the selected interface, or replace it with a project driver sized for the measured motor and protected by current limiting and interlocks.
9. Remove the yellow enclosure, external cable, buttons, and knob from normal operation.

An electrically emulated legacy button input is a circuit interface, not an instruction for a person to press a button.

## Required interlocks

- Hardware and firmware prevent forward and reverse from being active together.
- Boot, reset, heartbeat loss, TTL expiry, and process/radio failure release both outputs.
- A command has maximum pulse duration and cooldown; measured current/temperature limits abort motion.
- The independent actuator cutoff interrupts motor power.
- Open-loop timing is labeled approximate. Repeatable named expressions require reliable position feedback and homing.

## Acceptance evidence

Record schematics, measurements, scope/logic traces, selected component ratings, fault-injection results, and a 1,000-cycle heat/travel test. A photo of motion or a successful single pulse is not sufficient.

## Stop conditions

Never attach MCU GPIO directly from photographs, share grounds by assumption, route motor current through logic pins, energize both directions, or buy the final driver/fuse before voltage and stall current are known.
