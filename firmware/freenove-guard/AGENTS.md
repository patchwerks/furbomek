# Freenove guarded overlay guide

This directory is a separate, source-auditable overlay for the pinned Freenove
FNHR gait library. It is not the existing `firmware/robot-safety` diagnostic,
not an installed-image identification, and not device qualification.

Current deployment and physical acceptance are recorded in `docs/hardware/`
at repository root:40 motor-off cycles and all8bounded native/Hermes powered
commands passed on the supported robot. This is not floor/unattended release,
watchdog-reset or general mechanical-repair qualification. Keep original private
images and calibration unchanged; interpret offsets using the emitted16-bit AVR
arithmetic, not host integer width.

Keep every change for this component under this directory. Do not modify the
existing safety package, hardware records, operation records, stock firmware,
or any device. Do not open serial devices, flash, read EEPROM, change network
state, or commit from this package.

The build copies pinned preimages into a temporary tree, normalizes only the
temporary copies, applies the checked-in patches, and emits artifacts outside
the source tree. `FNHRBasic` is retained for the vendor gait, geometry, and
calibration reads. `FNHRComm` and ESP8266 actuator dispatch are excluded. The
UNO is a validating USB/RF relay and deliberate manual client only; the Mega
owns Guard state, source ownership, reply routing, and RF-loss expiry. RF24
replies use bounded listen/write/listen exchanges. Serial2 is a nonblocking,
read-only ESP compatibility surface for echo and supply only; it never enters
the actuator dispatcher or a Guard callback.

All motion-capable paths are behind the pure `Guard` state machine. Timer2 is
the sole Guard and UART owner; the main loop only executes one pending vendor
gait operation. Boot starts with A15/PK7 and A14/PK6 low and D22-D39 low. Those
V3.1 reference enables are active-high TD1583 signals; A13 is not used. Timer4
is reserved for a 10 ms cutoff, including operation deadlines, and the only
watchdog feed. STOP is exact `80 30 81`, checked before RF ownership or frame
parsing, unconditional, and terminal until reset. `.init3` clears MCUSR,
disables inherited WDT, and establishes safe outputs before constructors. A
blocked main thread is fail-stop only through the Timer4 cutoff; cooperative
abort is not claimed.

Run `check-safety.sh`, `test.sh`, and `build.sh --all` with the extracted
toolchain. Never describe an artifact as preserving the installed gait release:
the installed application release is unknown. The package preserves the
pinned vendor reference gait source through a reproducible overlay only.

Normal DISARM must quiesce hardware before ACK and may resume only through exact
next global sequence plus changed session ID. It never clears Fault. Emergency
STOP, parser faults and expired deadlines stay reset-only. Save/restore only
Servo compare bits and restore PWM with EN low before40ms/20ms bank staging.
Use one atomic paired Timer4 tick/millisecond sample per UART/RF event and mirror
deadline; never reuse a pre-gait callback clock after heavy `Robot.Update` work.
Only duplicate latest KEEP/STATUS may return fresh QueryReplay10 snapshots,
without sequence/lease/callback changes. Never retry or deduplicate actuation.

STOP ACKs route to their requesting ingress even while a different session owns
the dispatcher. Do not clear ownership early to achieve this: a pending ARM ACK
must still reach its owner, and safe-stop must precede the STOP ACK. The native
route/state matrix is software evidence only. The STOP routing candidate is not
installed; follow the root wired-maintenance protocol before device qualification.
