#!/usr/bin/env bash
set -euo pipefail
repo=$(realpath "$(dirname "$0")/../..")
media=${FURBOMEK_MEDIA_ROOT:-/data/furbomek-media}
mkdir -p "$media/godot" "$media/models"
chmod 700 "$media"
source_dir="$media/libfreenect2-source"
if [[ ! -d $source_dir/.git ]]; then
  GIT_MASTER=1 git clone --depth 1 --branch v0.2.1 https://github.com/OpenKinect/libfreenect2.git "$source_dir"
fi
[[ $(GIT_MASTER=1 git -C "$source_dir" rev-parse HEAD) == fd64c5d9b214df6f6a55b4419357e51083f15d93 ]] || \
  { printf '%s\n' 'Unexpected libfreenect2 source revision.' >&2; exit 1; }
cmake -S "$source_dir" -B "$media/libfreenect2-build" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$media/libfreenect2" -DENABLE_OPENGL=ON \
  -DENABLE_OPENCL=OFF -DENABLE_CUDA=OFF -DENABLE_VAAPI=OFF \
  -DENABLE_TEGRAJPEG=OFF -DBUILD_OPENNI2_DRIVER=OFF
cmake --build "$media/libfreenect2-build" --parallel 8
cmake --install "$media/libfreenect2-build"
cmake -S "$repo/services/camera-capture" -B "$media/capture-build" \
  -DCMAKE_PREFIX_PATH="$media/libfreenect2" -DCMAKE_BUILD_TYPE=Release
cmake --build "$media/capture-build" --parallel 8
archive="$media/godot-4.7.2.zip"
if [[ ! -f $archive ]]; then
  curl -fL https://github.com/godotengine/godot-builds/releases/download/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64.zip -o "$archive"
fi
printf '%s  %s\n' cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4 "$archive" | sha256sum --check --status
unzip -o "$archive" -d "$media/godot"
mv "$media/godot/Godot_v4.7.2-stable_linux.x86_64" "$media/godot/godot"
for model in pose_landmarker_lite.task blaze_face_short_range.tflite; do
  if [[ ! -f $media/models/$model ]]; then
    case $model in
      pose_landmarker_lite.task) url=https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task ;;
      blaze_face_short_range.tflite) url=https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite ;;
    esac
    curl -fL "$url" -o "$media/models/$model"
  fi
done
printf '%s  %s\n' 59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a "$media/models/pose_landmarker_lite.task" \
  b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f "$media/models/blaze_face_short_range.tflite" | sha256sum --check --status
uv run --no-project --python /usr/bin/python3.12 "$repo/services/camera-capture/track.py" --help
printf '%s\n' 'Build ready. See docs/operations/kinect2-host.md for dependencies, permissions and launch.'
