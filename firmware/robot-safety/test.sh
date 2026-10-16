#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
output_dir=$(mktemp -d "${TMPDIR:-/tmp}/robot-safety-test.XXXXXX")
trap 'rm -rf "$output_dir"' EXIT
"$root_dir/build.sh" --native --output-dir "$output_dir"
"$output_dir/native/robot-safety-tests"
printf 'native tests passed\n'
