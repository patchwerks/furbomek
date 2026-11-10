#!/usr/bin/env bash
set -euo pipefail

output=${1:?usage: build-x11-window-capture.sh OUTPUT}
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$(dirname -- "$output")"
cc -std=c11 -O2 -Wall -Wextra -Werror -fstack-protector-strong -D_FORTIFY_SOURCE=2 -D_POSIX_C_SOURCE=200809L \
  "$source_dir/x11-window-capture.c" -o "$output" \
  -Wl,-z,relro,-z,now -lX11 -l:libXcomposite.so.1
chmod 0700 "$output"
