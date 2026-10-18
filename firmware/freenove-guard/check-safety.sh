#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source_files=("$root_dir/include" "$root_dir/src" "$root_dir/avr")
for token in A13 EEPROM.write requestMoveLeg requestCalibrate requestInstallState requestTwistBody; do
  if grep -R -n -E "$token" "${source_files[@]}"; then
    printf 'forbidden token: %s\n' "$token" >&2
    exit 1
  fi
done
[[ $(grep -R -h 'TIMER4_COMPA_vect' "$root_dir/avr" | wc -l) -eq 1 ]]
[[ $(grep -R -h 'wdt_reset' "$root_dir/avr" | wc -l) -eq 1 ]]
[[ $(grep -R -h '0x30' "$root_dir/src" "$root_dir/include" | wc -l) -ge 1 ]]
grep -q 'section(".init3")' "$root_dir/avr/guard_main.cpp"
grep -q 'operation_deadline_tick' "$root_dir/avr/guard_runtime.cpp"
grep -q 'guard_service_active' "$root_dir/avr/guard_runtime.cpp"
grep -q 'Serial2' "$root_dir/avr/guard_runtime.cpp"
grep -q 'EspDiagnostics' "$root_dir/avr/guard_service.cpp"
! grep -q 'dispatcher' "$root_dir/src/esp_diag.cpp"
printf 'guard source scan passed\n'
