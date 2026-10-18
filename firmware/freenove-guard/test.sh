#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
output_dir=$(mktemp -d "${TMPDIR:-/tmp}/freenove-guard-test.XXXXXX")
trap 'rm -rf "$output_dir"' EXIT

"$root_dir/check-safety.sh"
"$root_dir/build.sh" --native --output-dir "$output_dir/build"
"$output_dir/build/native/freenove-guard-tests"
help_output=$("$output_dir/build/native/freenove-guard-driver" --help)
printf '%s\n' "$help_output" | grep -q 'computer begin'
busy_output=$(printf 'computer begin\ncomputer arm\ncomputer exec crawl\ncomputer exec sleep\ndone\ncomputer status\nquit\n' | "$output_dir/build/native/freenove-guard-driver")
expiry_output=$(printf 'computer begin\ncomputer arm\ntick 501\nquit\n' | "$output_dir/build/native/freenove-guard-driver")
printf '%s\n' "$busy_output" | grep -q 'result=BUSY'
printf '%s\n' "$busy_output" | grep -q 'RADIO robot->RF_COMPUTER result=ACCEPTED'
printf '%s\n' "$expiry_output" | grep -q 'state=FAULT'
printf '%s\n' "$expiry_output" | grep -q 'MOTION safe-stop'
disarm_output=$(printf 'computer begin\ncomputer arm\ncomputer disarm\ncomputer status\nquit\n' | "$output_dir/build/native/freenove-guard-driver")
printf '%s\n' "$disarm_output" | grep -q 'MOTION disarm'
printf '%s\n' "$disarm_output" | grep -q 'state=DISARMED'
actions_output=$(printf 'computer begin\ncomputer arm\ncomputer exec active\ndone\ncomputer exec sleep\ndone\ncomputer exec crawl-forward\ndone\ncomputer exec crawl-backward\ndone\ncomputer exec crawl-left\ndone\ncomputer exec crawl-right\ndone\ncomputer exec turn-left\ndone\ncomputer exec turn-right\ndone\nquit\n' | "$output_dir/build/native/freenove-guard-driver")
[[ $(printf '%s\n' "$actions_output" | grep -c 'MOTION exec=') -eq 8 ]]
restart_output=$(printf 'computer status\nquit\n' | "$output_dir/build/native/freenove-guard-driver")
printf '%s\n' "$restart_output" | grep -q 'state=BOOT'
printf 'freenove-guard native checks passed\n'
