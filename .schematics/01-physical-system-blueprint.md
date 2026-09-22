# Sheet 01 — Physical system blueprint

Companion image: [01-physical-system-blueprint.png](./01-physical-system-blueprint.png)

## Purpose

Locate the observed subsystems and define where present evidence ends. This sheet is not a dimensional drawing, center-of-gravity analysis, load calculation, or wiring diagram.

## Label status

| Feature | Status | What is supportable |
|---|---|---|
| Six-leg chassis and 18 hobby servos | Observed; platform identity inferred | Geometry is visible and consistent with FNK0031; exact servo and board revisions are TBD |
| Furby-like head and coupled mechanism | Observed; generation inferred | A salvaged animated head is installed; original 1998-era architecture is the closest cited analogue, not confirmed identity |
| Dual-cell bay and harness | Observed | Cell chemistry, series/parallel topology, protection, capacity, polarity, and health are TBD |
| Yellow head-control deck | Observed legacy assembly | Useful for reverse-engineering only; not part of the final external runtime |
| Robot-mounted gateway location | Proposed | Must be enclosed, strain-relieved, thermally acceptable, radio-tested, and serviceable |

## Final physical boundary

The robot carries the command receiver and last-line controller. Offboard Linux hosts provide planning, speech, perception, and OBS, but only authenticated bounded messages cross the radio. The robot-mounted MCU/radio and isolation/driver board own TTL expiry, watchdog, head-direction interlock, and immediate stop. Short internal links connect them to the motion controller and internal head driver.

The handheld movement remote and yellow facial-control box may be used only during controlled characterization. They are absent in normal operation. Any retained yellow-deck PCB must be internal; external buttons, knob, cable, and human control authority are removed.

## Measurements required before mounting hardware

1. Record total mass, head mass, center of gravity, chassis clearances, gait envelope, cable sweep, and tipping margin.
2. Identify cells, protection, charger, rail voltages, idle current, servo peak/stall current, head-motor stall current, and brownout behavior.
3. Measure enclosure space, airflow, heat, RF shadowing, and antenna separation.
4. Verify every harness route at all joint extremes and add strain relief and abrasion protection.
5. Demonstrate a physical actuator-power cutoff with the logic/telemetry rail state documented.

## Sources

- [Freenove FNK0031 product page](https://store.freenove.com/products/fnk0031)
- [Freenove component list](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/List.html)
- [US6149490A Furby mechanism patent](https://patents.google.com/patent/US6149490A/en)

## Stop conditions

Do not buy replacement batteries, change power topology, add a final enclosure, or operate unsupported until markings, polarity, protection, current, balance, and clearance are measured.
