#!/usr/bin/env bash
# Trusted orchestration only; candidate package/code execution stays in workers.
set -euo pipefail
case ${1:-} in media|legacy) mode=$1 ;; *) echo 'usage: worker.sh media|legacy CANDIDATE_DIRECTORY' >&2; exit 2 ;; esac
[[ $# == 2 && -n $2 && -d $2 ]] || { echo 'Explicit candidate directory is required' >&2; exit 2; }
candidate=$(cd "$2" && pwd -P)
trusted=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
[[ $candidate != "$trusted" ]] || { echo 'Trusted helpers must be separate from candidate source' >&2; exit 2; }
python_image=python:3.12.11-bookworm@sha256:1b48a1b13ec678be8d84974541cc007d4367aaf01f985231daad1a940106efc0
node_image=node:22.16.0-bookworm@sha256:a676f1268cf25605dbee49dcc3c73497311288da421855bdf19f25b8da6a95df
image=$python_image
if [[ $mode == legacy ]]; then image=$node_image; fi
ci_id="furbomek-${mode}-$$"
network="$ci_id-net"
volume="$ci_id-work"
proxy="$ci_id-proxy"
cleanup() {
  local result=${1:-$?}
  if [[ $result != 0 ]]; then docker logs "$proxy" 2>&1 || true; fi
  docker rm -f "$proxy" >/dev/null 2>&1 || true
  docker volume rm -f "$volume" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker pull "$python_image"
if [[ $image != "$python_image" ]]; then docker pull "$image"; fi
docker network create --internal --opt com.docker.network.bridge.gateway_mode_ipv4=isolated "$network" >/dev/null
docker volume create --driver local --opt type=tmpfs --opt device=tmpfs \
  --opt o=size=4g,uid=1000,gid=1000,mode=0700 "$volume" >/dev/null
docker run -d --name "$proxy" --read-only --cap-drop ALL --security-opt no-new-privileges \
  --user 1000:1000 --cpus 1 --memory 128m --pids-limit 64 \
  --mount "type=bind,source=$trusted/tools/ci/dependency-proxy.py,target=/proxy.py,readonly" \
  "$python_image" python -B /proxy.py >/dev/null
docker network connect --alias dependency-proxy "$network" "$proxy"
# Wait on the listener instead of mistaking startup refusal for policy denial.
ready=false
for attempt in {1..15}; do
  if docker exec "$proxy" python -c 'import socket; socket.create_connection(("127.0.0.1", 3128), timeout=1).close()'; then
    ready=true
    break
  fi
  sleep 1
done
[[ $ready == true ]] || { echo 'Dependency proxy did not become ready' >&2; exit 1; }

# No runner environment, home, socket or writable host directory is forwarded.
worker=(docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges
  --user 1000:1000 --cpus 2 --memory 4g --pids-limit 256
  --tmpfs /tmp:rw,exec,nosuid,size=512m
  --mount "type=bind,source=$candidate,target=/source,readonly"
  --mount "type=volume,source=$volume,target=/scratch"
  --mount "type=bind,source=$trusted/tools/ci/provision-python.sh,target=/trusted/provision-python.sh,readonly"
  --workdir /scratch --env XDG_CACHE_HOME=/scratch/cache
  --env UV_CACHE_DIR=/scratch/uv-cache --env UV_PYTHON_DOWNLOADS=never
  --env PYTHONUNBUFFERED=1 --env PYTHONDONTWRITEBYTECODE=1
  --env npm_config_cache=/scratch/npm-cache)
proxy_env=(--env HTTPS_PROXY=http://dependency-proxy:3128 --env HTTP_PROXY=http://dependency-proxy:3128
  --env https_proxy=http://dependency-proxy:3128 --env http_proxy=http://dependency-proxy:3128
  --env NO_PROXY= --env no_proxy=)

"${worker[@]}" --network "$network" "${proxy_env[@]}" "$image" bash -euc '
  test "$(id -u)" != 0
  test ! -e /var/run/docker.sock
  # Assert both direct external egress and a forbidden proxy destination fail.
  if curl --noproxy "*" -fsSI --connect-timeout 3 https://pypi.org; then exit 1; fi
  forbidden=$(curl -sSI --connect-timeout 3 --output /dev/null --write-out "%{http_connect}" https://example.com || true)
  test "$forbidden" = 403
  curl -fsSI --retry 3 --retry-connrefused --connect-timeout 10 https://pypi.org >/dev/null
  cp -R /source/. /scratch/source
  mkdir -p /scratch/cache
'
if [[ $mode == media ]]; then
  "${worker[@]}" --network "$network" "${proxy_env[@]}" "$image" bash -euc '
    /usr/local/bin/python3 -I -m venv /scratch/bootstrap
    /scratch/bootstrap/bin/pip install --only-binary=:all: --no-deps uv==0.11.7
    bash /trusted/provision-python.sh /scratch/source /scratch/python-envs \
      /scratch/uv-cache /scratch/bootstrap/bin/uv /usr/local/bin/python3
    # Explicit base interpreter: never discover or re-query a dependency env.
    /scratch/bootstrap/bin/uv --no-config pip install --python /usr/local/bin/python3 \
      --only-binary=:all: --target /scratch/build-inputs hatchling==1.27.0
  '
  # Fixed, hash-verified tool download is outside candidate execution.
  ci_tools=$(mktemp -d)
  trap 'result=$?; rm -rf "$ci_tools"; cleanup "$result"' EXIT
  curl -fL --retry 3 https://github.com/godotengine/godot-builds/releases/download/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64.zip -o "$ci_tools/godot.zip"
  printf '%s  %s\n' cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4 "$ci_tools/godot.zip" | sha256sum --check
  unzip -q "$ci_tools/godot.zip" -d "$ci_tools"
  "${worker[@]}" --network none --env UV_OFFLINE=1 \
    --mount "type=bind,source=$ci_tools,target=/tools,readonly" "$image" bash -euc '
    export PATH=/scratch/bootstrap/bin:$PATH
    export FURBOMEK_GODOT=/tools/Godot_v4.7.2-stable_linux.x86_64
    # Candidate paths are replaced only after network-none begins. The helper
    # validated project directories during provisioning; no candidate ran since.
    for service in embodiment-gateway hermes-activity stream-supervisor; do
      project=/scratch/source/services/$service
      resolved=$(cd "$project" && pwd -P)
      case "$resolved" in /scratch/source/*) ;; *) exit 1 ;; esac
      rm -rf -- "$project/.venv"
      ln -s "/scratch/python-envs/$service" "$project/.venv"
    done
    cd /scratch/source
    git -c safe.directory=/scratch/source diff --exit-code HEAD -- .
    bash tools/verify.sh dispatcher media
  '
else
  "${worker[@]}" --network "$network" "${proxy_env[@]}" "$image" bash -euc '
    cd /scratch/source
    npm ci --ignore-scripts --no-audit --no-fund
    npm ci --prefix server --ignore-scripts --no-audit --no-fund
  '
  "${worker[@]}" --network none "$image" bash -euc '
    cd /scratch/source
    git -c safe.directory=/scratch/source diff --exit-code HEAD -- .
    bash tools/verify.sh legacy
  '
fi
