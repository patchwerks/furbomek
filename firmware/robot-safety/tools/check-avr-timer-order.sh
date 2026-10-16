#!/usr/bin/env bash
set -euo pipefail

objdump_file=${1:?objdump file required}
function_file=$(mktemp "${TMPDIR:-/tmp}/robot-safety-timer.XXXXXX")
trap 'rm -f "$function_file"' EXIT
awk '
/configure_timer1Ev>:/ { inside=1; print; next }
inside && /^0000[0-9a-f]+ </ { exit }
inside { print }
' "$objdump_file" > "$function_file"

require_order() {
  local previous=0
  local pattern line
  for pattern in "$@"; do
    line=$(rg -n "$pattern" "$function_file" | awk -F: -v previous="$previous" '$1 > previous { print $1; exit }' || true)
    [[ -n "$line" && "$line" -gt "$previous" ]] || {
      printf 'timer disassembly order failure: %s\n' "$pattern" >&2
      cat "$function_file" >&2
      exit 1
    }
    previous=$line
  done
}

require_order \
  'cli' \
  'st[[:space:]]+X,[[:space:]]+r1' \
  'st[[:space:]]+Z,[[:space:]]+r1' \
  'sts[[:space:]]+0x0080' \
  'sts[[:space:]]+0x0085' \
  'sts[[:space:]]+0x0084' \
  'out[[:space:]]+0x16' \
  'sts[[:space:]]+0x0089' \
  'sts[[:space:]]+0x0088' \
  'st[[:space:]]+Z,[[:space:]]+r25' \
  'st[[:space:]]+Z,[[:space:]]+r25' \
  'st[[:space:]]+X,[[:space:]]+r24'

cat "$function_file"
printf 'timer-order=PASS\n'
