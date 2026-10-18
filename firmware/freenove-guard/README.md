# Freenove guarded overlay

This package is a reproducible, narrowly scoped ATmega2560 overlay for the
pinned Freenove FNHR reference source. It preserves the vendor gait geometry
and calibration-offset reads in a temporary patched tree while replacing the
stock command/transport shell with a guarded Mega dispatcher, a USB/RF UNO
relay, and the preserved manual joystick packet vocabulary.

It passed a temporary motor-off hardware test on 2026-10-17; both originals were
restored and full flash/EEPROM verification passed. A compatible guarded bench
repeatable guard has since passed40 motor-off cycles and recorded native and
actual Hermes powered acceptance for all eight bounded actions on the support.
Each normal action disarmed without reset; final explicit STOP verified Fault4.
Both EEPROMs remain unchanged. This is not floor-locomotion, unattended-operation
or authentication qualification. See the authoritative
`active_deployment` in `../../docs/hardware/firmware.json` for current artifacts.

## Actual motor-off hardware result, 2026-10-17

With freshly operator-confirmed POWER OFF, the real Brodex USB → UNO → RF → Mega
→ RF → UNO → USB path returned CRC-validated robot replies for boot status,
BEGIN, staged ARM, software Active acceptance/busy, STOP to FAULT and rejected
rearm. Host heartbeat loss and malformed heartbeat traffic both caused local
fault without a Wi-Fi STOP connection. The initial driver incorrectly expected
a rejected ARM to echo its proposed sequence rather than the last accepted one;
the corrected driver passed without a firmware change.

Only application flash was written. No EEPROM, bootloader, fuse or lock writes
were requested. Original applications were then restored and complete flash and
EEPROM verification passed against both private baselines. Artifact hashes,
commands and rollback limits are recorded in `../../docs/hardware/firmware.json`.

This does not establish electrical cutoff, watchdog-reset behavior, manual
gestures, ESP diagnostics or powered motion. The earlier claim that all-FF
calibration decodes as a large offset was wrong: installed and candidate AVR
machine code both use signed 16-bit arithmetic and decode it as -0.01 degrees.
The preserved calibration is compatible with the candidate's emitted decoder;
no calibration bytes need rewriting. Supported powered acceptance is still a
separate physical test, beginning with disarmed power-on, then ARM alone.

## Guard contract

- Reset boots with `A15/PK7` and `A14/PK6` low and D22-D39 low.
- V3.1 enable signals are treated as active-high TD1583 inputs with pulldowns;
  A13 and AO4407 assumptions are excluded.
- Arduino `.init3` clears `MCUSR`, disables inherited WDT, and drives the
  enable/output pins safe before constructors. Timer4 compare A
  runs every 10 ms, owns the cutoff path, and is the only watchdog freshness
  feed. The watchdog is configured for 250 ms.
- Timer2 is the sole Guard/serial owner and remains active while the main loop
  performs one bounded vendor gait operation. A non-reentrant service latch
  prevents `sei()` from re-entering that service. The Timer4 path cuts both
  enables first, disables Servo compare interrupts, then forces D22-D39 low.
  The main thread may remain blocked in vendor gait code until reset; no
  cooperative abort or busy-flag clearing is claimed.
- Transport expiry is 500 ms. A session has a hard 30 s limit. An operation
  has a hard 3 s limit enforced independently by Timer4. `EXEC` never renews
  transport; only `KEEPALIVE` does.
- STOP is the exact three-byte sequence `80 30 81`; it ignores CRC, session,
  and sequence state. STOP and deadline expiry enter terminal `FAULT` until
  reset. A hardware watchdog reset instead returns to disarmed boot. The
  preserved bootloader clears `MCUSR`, so this application cannot identify
  watchdog resets or promise a persistent fault latch across reset.
- ARM requires only EEPROM data-format byte 0 equal to 1 and product byte 3
  equal to 30, 31, or 32. EEPROM is read-only in this build. The vendor
  `RobotAction::Start` path does not own byte 140 or boot persistence. Erased
  calibration bytes must be interpreted using the emitted AVR instructions,
  not host integer arithmetic. The preserved FF pairs decode as -0.01 degrees
  in both installed and candidate images. Do not rewrite them to host-computed
  values; require supported observation before qualifying powered motion.
- `DISARM` is `80 36 ...` with the normal body/CRC envelope. It is accepted only
  by the owner in `SESSION` or healthy idle `ARMED`, with the exact next
  sequence. Hardware quiescence completes before the `DISARMED` reply; it never
  clears a terminal fault. `BEGIN 0` is for `BOOT`; a resumed `BEGIN` uses the
  exact next sequence and a changed RAM-only identifier. Status in `BOOT`,
  `FAULT`, or `DISARMED`, and supply queries in every state, are read-only.
- A duplicate of the last accepted active `KEEPALIVE` or `STATUS` query is
  acknowledged once by matching opcode and sequence. The duplicate check runs
  after active TTL checks and before exact-next validation; it returns fresh
  state, fault, busy, and remaining fields without advancing sequence, renewing
  transport, invoking motion callbacks, or refreshing Timer4. Older, reordered,
  opcode-mismatched, and mutation frames are rejected. This is finite ordering,
  not authentication.
- The Mega is the sole `Guard` and ownership authority. A computer or deliberate
  manual client acquires the one RF session only after an accepted `BEGIN`; the
  owner stays fixed until terminal fault or reset. Computer heartbeats remain
  host-originated; the manual client alone sends a monotonic guarded KEEPALIVE
  every 100 ms after the robot has acknowledged ARM.
- The manual client holds joystick button D7 for one second and releases it to
  request `BEGIN`, then `ARM`; it enables joystick output only after robot RF
  acknowledgements. D4/D3/D2 held active send one three-write STOP burst without
  waiting for a response. Accepted raw manual packets are exact vendor echo,
  switch, crawl, height, move, and twist shapes only. Vendor echo never renews
  the manual lease or operation deadline.
- Serial2 nonblockingly restores the vendor AT SoftAP server sequence and parses
  `+IPD` frames. It answers only echo and supply through `CIPSEND`; it has no
  actuator request parsing and cannot enter Guard or vendor dispatch.

## Protocol

The guarded frames are `80 length body crc0 crc1 crc2 81`. Every frame byte
between delimiters is strictly 7-bit. The length is the body length and is
bounded to 4-20. CRC-16/CCITT-FALSE covers the length and body; its 16-bit value
is encoded as three 7-bit groups. Command bodies use an opcode, a 21-bit
strictly increasing sequence, and an optional action or 8-byte correlation
identifier encoded as 7-bit pairs.

Commands and odd replies are:

| Request | Reply | Meaning |
| --- | --- | --- |
| `28` | `29` | BEGIN with host CSPRNG correlation identifier |
| `2a` | `2b` | ARM after supported V3 metadata check |
| `2c` | `2d` | KEEPALIVE and transport renewal |
| `2e` | `2f` | EXEC one semantic quantum: active, sleep, crawl forward/backward/left/right, or turn left/right |
| `32` | `33` | STATUS |
| `34` | `35` | Read-only controller supply query |
| `36` | `37` | DISARM and hardware-quiesce acknowledgement |

`BEGIN` replies omit the redundant identifier echo, keeping every RF envelope
at or below the nRF24 32-byte payload limit. The host identifier is correlation
only and is not authentication. Exact global ordering is finite and resets with
the MCU; it does not provide authenticated freshness. Authentication, independent
watchdog-reset characterization and unattended/floor release remain outside the
supported operator-present acceptance.

Supply query uses the same four-byte request body as `STATUS`: `34 seq0 seq1
seq2`. Its sixteen-byte `35` reply keeps result, state, last accepted sequence,
fault, and busy fields unchanged. Only its two 7-bit groups at bytes 8 and 9
encode controller-reported centivolts, low group first. It is accepted in BOOT
and FAULT without `BEGIN` or `ARM`, does not consume a sequence or renew a
lease, and replies to the query ingress without changing the owned session's
reply route. It is not evidence of physical power state, battery charge, or a
motor-power cutoff.
Echo `80 00 81` and supply `80 0a 81` remain read-only compatibility responses;
all other legacy stock frames are rejected by omission from the build.

## Qualification boundary

**SUPPORTED OPERATOR-PRESENT CONTROL ONLY.** The installed guard/RF bridge and
current Hermes profile actually passed all eight bounded powered commands. This
does not authorize unattended use or certify physical cutoff latency/current,
floor travel, radio range or manual gesture hardware. Preserve original private
images and EEPROM; do not treat arbitrary builds as qualified replacements.
Known limits include no authenticated session freshness, measured V3.1 rail/torque
behavior or guaranteed reset of a main thread blocked inside vendor
gait code. UART service is bounded to 32 received bytes per Timer2 callback and
UART replies remain contingent on TX space; neither behavior is a production
transport guarantee. Serial2 intentionally omits all ESP actuator commands.
The UNO image is additionally limited to a conservative `< 30720`-byte
`.text`/`.data` binary, reserving the top 2 KiB of its 32 KiB address space.
This is a build bound, not a claim about the installed board's fuse or
bootloader boundary; no remote image is written until that boundary is read and
qualified.

## Reproducible build

No host tools are installed and no network or device is accessed:

```sh
firmware/freenove-guard/check-safety.sh
firmware/freenove-guard/test.sh
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/freenove-guard/build.sh --all \
  --output-dir /tmp/freenove-guard-build-a
AVR_ROOT=/tmp/opencode/furbomek-avr-toolchain \
  firmware/freenove-guard/build.sh --avr \
  --output-dir /tmp/freenove-guard-build-b
cmp /tmp/freenove-guard-build-a/avr/guard.elf /tmp/freenove-guard-build-b/avr/guard.elf
cmp /tmp/freenove-guard-build-a/avr/guard.hex /tmp/freenove-guard-build-b/avr/guard.hex
```

Inputs are checked against the pinned FNHR source, official FNHR/Servo/
FlexiTimer2 archives, ArduinoCore-avr commit `42fa4a1ea1b1b11d1cc0a60298e529d37f9d14bd`
(1.8.6), and the extracted AVR compiler tuple. The final report includes
preimage hashes, ELF/HEX hashes, size, undefined symbols, vector symbols, and
temporary overlay patch output. The HEX excludes `.eeprom` and is checked below
the ATmega2560 boot-region boundary `0x3e000`.

## Attribution and license

The overlay is a derivative adaptation of Freenove FNHR V12.6, dated
2023-09-19, from official repository commit
`1596c5ffe07a262fa7dc6d0189de6c2321270278`. Attribution, source provenance, and
the original CC BY-NC-SA 3.0 URI are retained in `vendor/NOTICE.txt`; the
overlay and any distribution of its derivative vendor portion must remain under
CC BY-NC-SA 3.0. This license grants no commercial permission. ArduinoCore,
Servo, and FlexiTimer2 remain separately licensed dependencies.
