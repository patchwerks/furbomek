# Sheet 04 — Control path blueprint

Companion image: [04-control-path-blueprint.png](./04-control-path-blueprint.png)

## Purpose

Define control authority, failure containment, and the transition from legacy controllers to an untethered robot-mounted gateway.

## Current versus final paths

| Path | Status | Runtime authority |
|---|---|---|
| Handheld remote -> robot wireless module -> motion controller | Legacy/reference | None in final normal operation |
| Yellow box/buttons/knob -> head motor | Legacy/observed | None in final normal operation |
| Stock USB/WLAN development path | Reference/bench | Characterization and controlled development only |
| Offboard Linux gateway service -> authenticated wireless link | Proposed | Validates semantic requests, identity, schema, mode, rate, lease |
| Robot-mounted MCU/radio + isolation/driver board | Proposed physical gateway | Final local authority for watchdog, TTL, interlock, stop, and translation |
| Internal motion/head controller links | Proposed/measured later | Short, enclosed, serviceable; no external legacy control cable |

## Command lifecycle

1. Hermes requests a named action such as `walk(forward, 0.2, 300 ms)`.
2. The offboard service validates identity, schema, policy, state, rate, mode, and lease.
3. The authenticated wireless protocol carries a version, sequence, action bounds, TTL, and integrity protection.
4. The robot-mounted gateway revalidates, acknowledges, and translates the action to local high-level motion/head commands.
5. Local watchdog and TTL stop the action whether or not a later packet arrives.
6. Telemetry and audit logs record request, decision, acknowledgement, expiry, stop, and fault.

The physical gateway—not Hermes and not the offboard service—owns last-line stop behavior.

## Failure matrix

| Failure | Required local outcome |
|---|---|
| Hermes or offboard service exits | Current TTL expires; gait stops; head outputs release |
| Wireless link disappears | Robot gateway enters defined safe state locally |
| Duplicate/stale/corrupt command | Reject; no extension of prior motion |
| Head forward/reverse conflict | Hardware and firmware reject/release |
| Video/OBS loss | Control applies its own policy; video is never the stop transport |
| Gateway MCU reset/brownout | Outputs default inactive; motion controller watchdog stops |
| Physical cutoff activated | Actuator power removed without software |

## Network boundary

Robot WLAN must not be routed directly to the public internet. Use per-device identity, replay protection, key rotation/revocation, least-privilege firewalling, and a separate maintenance path. Radio range is not a safety guarantee; test degraded links and total loss.

## Sources

- [Freenove default control paths](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Default_Functions.html)
- [Freenove programming guide](https://docs.freenove.com/projects/fnk0031/en/latest/fnk0031/codes/tutorial/Programming.html)
- [systemd watchdog documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [MAVLink heartbeat protocol as a reference pattern](https://mavlink.io/en/services/heartbeat.html)

## Stop conditions

Do not connect Hermes until simulator, replay/stale rejection, watchdog, TTL, STOP priority, and real loss-of-link tests pass. Do not call an offboard Linux process an “isolated microcontroller gateway.”
