#!/usr/bin/env bash
# Accepted helper code only. Never load this script from candidate source.
set -euo pipefail
[[ $# == 5 ]] || { echo 'usage: provision-python.sh SOURCE ENV_ROOT CACHE UV PYTHON' >&2; exit 2; }
source=$(cd "$1" && pwd -P)
envs=$2
cache=$3
uv=$4
python=$5
for path in "$envs" "$cache" "$uv" "$python"; do
  [[ $path == /* ]] || { echo 'Absolute trusted paths required' >&2; exit 2; }
done
[[ -x $uv && -x $python ]] || exit 2
# Resolve parent directories without following an existing destination. mkdir
# (without -p) rejects reused paths, including dangling or directory symlinks.
envs="$(cd "$(dirname "$envs")" && pwd -P)/$(basename "$envs")"
cache="$(cd "$(dirname "$cache")" && pwd -P)/$(basename "$cache")"
for path in "$envs" "$cache"; do
  case "$path/" in "$source/"*) echo 'State must be outside candidate source' >&2; exit 2 ;; esac
done
mkdir -- "$envs"
mkdir -- "$cache"
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV CONDA_PREFIX UV_PROJECT_ENVIRONMENT UV_PYTHON UV_PYTHON_PATH UV_CONFIG_FILE
export UV_CACHE_DIR="$cache" UV_PYTHON_DOWNLOADS=never UV_NO_CONFIG=1 PYTHONNOUSERSITE=1
# Work from helper-owned state, never the candidate cwd (sitecustomize, etc.).
cd "$envs"
for service in embodiment-gateway hermes-activity stream-supervisor; do
  project=$(cd "$source/services/$service" && pwd -P)
  case "$project/" in "$source/"*) ;; *) echo 'Project escapes candidate source' >&2; exit 2 ;; esac
  # Each fresh environment is touched once while registry egress is available.
  UV_PROJECT_ENVIRONMENT="$envs/$service" "$uv" --no-config sync \
    --python "$python" --frozen --no-install-project --no-build --project "$project"
done
script=$(realpath -e "$source/services/camera-capture/tests/test_snapshot.py")
case "$script" in "$source/"*) ;; *) echo 'Script escapes candidate source' >&2; exit 2 ;; esac
"$uv" --no-config sync --python "$python" --frozen --no-build --script "$script"
