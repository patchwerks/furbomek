#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
command -v rg >/dev/null || { printf '%s\n' 'ripgrep is required for the safety source scan' >&2; exit 2; }
if rg -n -i 'FNHR|Freenove|Arduino|\bServo\b|\bgait\b|\bhead\b|EEPROM|wdt_enable|WDTCSR|analogWrite|digitalWrite|\bPORT[A-Z]\b|\bDDR[A-Z]\b|avrdude|upload' \
  "$root_dir/include" "$root_dir/src" "$root_dir/avr" "$root_dir/tools/driver.cpp"; then
  printf '%s\n' 'forbidden actuator, vendor, persistence, watchdog, or device-access token found' >&2
  exit 1
fi
if rg -n '(^|[^A-Za-z])std::|new[[:space:]]|delete[[:space:]]|malloc|free[[:space:]]*\(' \
  "$root_dir/include" "$root_dir/src" "$root_dir/avr"; then
  printf '%s\n' 'heap or host-library token found in shared/AVR code' >&2
  exit 1
fi
printf '%s\n' 'safety source scan: no actuator, vendor, EEPROM, watchdog, device, heap, or host-library tokens'
