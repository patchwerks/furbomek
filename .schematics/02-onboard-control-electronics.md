# Sheet 02 — Onboard control electronics

Companion image: [02-onboard-control-electronics.png](./02-onboard-control-electronics.png)

## Purpose

Separate photographed electronics from platform-derived identifications and from the proposed robot-mounted gateway.

## Evidence table

| Element | Status | Limitation |
|---|---|---|
| Crawling-robot controller and servo headers | Observed; ATmega2560 signature measured via bootloader | Exact board revision, power distribution, and pin map remain unqualified; installed flash/EEPROM backed up and verified |
| WLAN module/socket | Observed ESP-01 / ESP8266EX markings | Radio firmware and WLAN behavior remain unqualified; original photo evidence is preserved |
| Optional wireless-remote module/socket | Observed/reference | Separate from WLAN; not required in the autonomous end state |
| 18 servo channels | Observed/reference | Ranges, calibration, current, and fault behavior require tests |
| Robot-mounted isolated gateway | Proposed | New physical MCU/radio plus watchdog, power conditioning, and protected isolation/driver stage |

Current unit evidence is in [`hardware.json`](../docs/hardware/hardware.json),
[`firmware.json`](../docs/hardware/firmware.json), and the
[original-photo index](../docs/hardware/evidence/README.md). These supersede the
earlier unknown MCU/WLAN labels in the planning image; do not restart discovery.

Freenove documents a robot-created WLAN and an optional two-module handheld remote. The programming guide also warns that custom code changes compatibility with Processing, Android, and remote modes. Stock USB echo and image preservation are now verified, but no motion/safety qualification follows from them.

## Autonomous control design

The handheld remote is retired from normal runtime. The proposed gateway rides on the robot and communicates wirelessly with the offboard service. It emits only local high-level motion commands to the crawling-robot controller, never public/raw servo writes. The robot-side firmware enforces:

- version and sequence validation;
- bounded speed, pose, gait, and update rate;
- short action TTL and link heartbeat;
- local neutral/stop on stale or invalid input;
- a priority `STOP` path independent of Hermes;
- telemetry for power, state, fault, and command acknowledgement.

Electrical isolation or appropriate level translation is selected after rail and interface measurements. “Isolation” must not be used as a vague software synonym.

## Bench sequence

1. Photograph both plug-in modules, controller silkscreen, MCU, regulator, connectors, and board revision.
2. Back up or identify installed firmware; document licenses before copying upstream code.
3. Support the chassis, limit actuator power, and establish an independent cutoff.
4. Characterize stock USB and WLAN behavior; capture messages and timeout behavior.
5. Build a simulator and contract tests before flashing gateway/controller changes.
6. Inject dropped packets, duplicate/stale sequences, corrupted frames, process death, and radio loss.

## Sources

- [Freenove default functions](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Default_Functions.html)
- [Freenove programming guide](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Programming.html)
- [Freenove Arduino IDE guide](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Arduino_IDE.html)
- [Official Freenove repository and license notice](https://github.com/Freenove/Freenove_Hexapod_Robot_Kit)

## Stop conditions

Do not flash unknown hardware, power a module from an assumed rail, route servo current through the new MCU, or claim fail-safe autonomy until loss-of-link tests pass on the actual controller.
