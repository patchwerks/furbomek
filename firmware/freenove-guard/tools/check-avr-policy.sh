#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
main_file=${1:?main source required}
runtime_file=${2:?runtime source required}
objdump_file=${3:?objdump report required}
vectors_file=${4:?vector report required}

grep -q 'section(".init3")' "$main_file"
grep -q 'MCUSR = 0' "$main_file"
grep -q 'TIMER4_COMPA_vect' "$main_file"
grep -q 'operation_deadline_tick' "$runtime_file"
grep -q 'operation_active' "$runtime_file"
grep -q 'guard_service_active' "$runtime_file"
grep -q 'saved_pwm_interrupts' "$runtime_file"
grep -q 'quiesce_outputs_locked(false)' "$runtime_file"
grep -q 'TIMSK1 &= static_cast<uint8_t>(~_BV(OCIE1A))' "$runtime_file"
grep -q 'TIMSK3 &= static_cast<uint8_t>(~_BV(OCIE3A))' "$runtime_file"
grep -q 'TIMSK5 &= static_cast<uint8_t>(~_BV(OCIE5A))' "$runtime_file"
grep -q 'freenove_guard::ClockSample clock_sample()' "$runtime_file"
grep -q 'mirror_transport_deadline' "$root_dir/avr/guard_service.cpp"
grep -q 'event_clock = clock_sample()' "$root_dir/avr/guard_service.cpp"
grep -q 'final_clock = clock_sample()' "$root_dir/avr/guard_service.cpp"
! grep -q 'guard_service(uint32_t' "$root_dir/avr/guard_service.cpp"
! grep -q 'sync_deadlines(now_ms' "$root_dir/avr/guard_service.cpp"
! grep -q 'millis()' "$runtime_file"
[[ $(grep -c 'PORTK |= _BV' "$runtime_file") -eq 2 ]]
grep -q 'TIMER4_COMPA_vect=__vector_42' "$vectors_file"
grep -q '__vector_42$' "$vectors_file"
grep -q '__vector_42' "$objdump_file"
grep -q 'TIMER4_COMPA_vect' "$main_file"
grep -q 'WDTO_250MS' "$runtime_file"
grep -q 'guard_init3' "$main_file"
grep -q 'dispatcher.tick' "$root_dir/avr/guard_service.cpp"
grep -q 'dispatcher.receive' "$root_dir/avr/guard_service.cpp"

python3 - "$main_file" "$runtime_file" <<'PY'
from pathlib import Path
import sys

main = Path(sys.argv[1]).read_text()
runtime = Path(sys.argv[2]).read_text()
loop = main[main.index("void loop()"):]
if "guard." in loop:
    raise SystemExit("main loop directly owns Guard state")
start = runtime.index("bool arm_start()")
end = runtime.index("bool arm_ready()", start)
if "robot_action.Start" in runtime[start:end]:
    raise SystemExit("ARM path performs vendor initialization")
PY

printf 'init3=present\n'
printf 'timer2_guard_owner=vendor_update\n'
printf 'timer4_vector=__vector_42\n'
printf 'operation_deadline=timer4-independent\n'
printf 'main_guard_access=none\n'
printf 'pwm_resume=saved_OCIE1A_OCIE3A_OCIE5A_mask_only\n'
printf 'clock_pairing=atomic_Timer4_ticks_and_derived_ms\n'
printf 'query_replay=result_10_keepalive_status_only\n'
