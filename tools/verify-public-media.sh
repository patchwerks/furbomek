#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
  printf 'Usage: bash tools/verify-public-media.sh [commit]\n' >&2
  exit 2
fi

cd -- "$(git rev-parse --show-toplevel)"
registry=docs/hardware/evidence/reviewed-media.sha256
scratch=$(mktemp -d)
trap 'rm -f -- "$scratch/paths" "$scratch/reviews"; rmdir -- "$scratch"' EXIT
if [[ $# -eq 0 ]]; then
  prefix=:
  git ls-files -z > "$scratch/paths"
else
  tree=$(git rev-parse --verify --end-of-options "${1}^{tree}")
  prefix="$tree:"
  git ls-tree -rz --name-only "$tree" > "$scratch/paths"
fi
git cat-file blob "$prefix$registry" > "$scratch/reviews"

digest_command=(shasum -a 256)
if command -v sha256sum >/dev/null; then
  digest_command=(sha256sum)
fi
shopt -s nocasematch
failed=0
while IFS= read -r -d '' media_file; do
  case "$media_file" in
    *.apng|*.avif|*.bmp|*.dng|*.gif|*.heic|*.heif|*.jpeg|*.jpg|*.png|*.tif|*.tiff|*.webp|*.3gp|*.avi|*.m2ts|*.m4v|*.mjpeg|*.mkv|*.mov|*.mp4|*.mpeg|*.mpg|*.ogv|*.webm)
      sha=$(git cat-file blob "$prefix$media_file" | "${digest_command[@]}")
      if ! grep -Fxq -- "${sha%% *}  $media_file" "$scratch/reviews"; then
        printf 'Media review missing or stale for %q\n' "$media_file" >&2
        failed=1
      fi
      ;;
  esac
done < "$scratch/paths"

if [[ $failed -ne 0 ]]; then
  printf 'See docs/hardware/evidence/README.md before publishing.\n' >&2
  exit 1
fi

printf 'Public media hashes match the reviewed files.\n'
