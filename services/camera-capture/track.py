# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["mediapipe==0.10.21", "opencv-contrib-python==4.11.0.86", "numpy==1.26.4", "pydantic==2.12.3", "typer==0.16.0"]
# ///
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import mediapipe as mp
import typer
from detect_targets import TrackState, assign_ids, detect
from mediapipe.tasks.python import BaseOptions, vision
from vision_frames import VisionFrame, frame_sequence_matches, load_snapshot


def main(inspect_image: Path | None = None, seconds: int = 0) -> None:
    directory = Path(os.environ.get("FURBOMEK_KINECT_DIR", f"/dev/shm/furbomek-kinect2-{os.getuid()}"))
    root = Path(os.environ.get("FURBOMEK_MEDIA_ROOT", "/data/furbomek-media"))
    models = root / "models"
    for name, expected in (
        ("pose_landmarker_lite.task", "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"),
        ("blaze_face_short_range.tflite", "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"),
    ):
        if hashlib.sha256((models / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Model hash mismatch: {name}")
    pose_options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(models / "pose_landmarker_lite.task"),
                                 delegate=BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.VIDEO, num_poses=2, min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6, min_tracking_confidence=0.6)
    face_options = vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(models / "blaze_face_short_range.tflite"),
                                 delegate=BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.VIDEO, min_detection_confidence=0.6)
    with vision.PoseLandmarker.create_from_options(pose_options) as pose, \
            vision.FaceDetector.create_from_options(face_options) as face:
        if inspect_image is not None:
            image = mp.Image.create_from_file(str(inspect_image))
            result = pose.detect_for_video(image, 1)
            faces = face.detect_for_video(image, 1)
            print(f"poses={len(result.pose_landmarks)} faces={len(faces.detections)}", flush=True)
            return
        state = TrackState()
        last_sequence = 0
        started = time.monotonic()
        while seconds == 0 or time.monotonic() - started < seconds:
            try:
                snapshot = load_snapshot(directory)
            except FileNotFoundError:
                time.sleep(0.02)
                continue
            if snapshot is None or snapshot.meta.sequence == last_sequence:
                time.sleep(0.01)
                continue
            age = time.monotonic_ns() - snapshot.meta.capture_monotonic_ns
            if age < 0 or age > 600_000_000:
                time.sleep(0.02)
                continue
            last_sequence = snapshot.meta.sequence
            candidates = detect(snapshot, (pose, face), models / "robot-template.png")
            if not frame_sequence_matches(directory / snapshot.meta.frame_file, last_sequence):
                continue
            if time.monotonic_ns() - snapshot.meta.capture_monotonic_ns > 600_000_000:
                continue
            observed_ns = time.monotonic_ns()
            state = assign_ids(candidates, state, observed_ns)
            output = VisionFrame(sequence=last_sequence,
                capture_monotonic_ns=snapshot.meta.capture_monotonic_ns,
                produced_monotonic_ns=time.monotonic_ns(), frame_file=snapshot.meta.frame_file,
                produced_unix_ms=time.time_ns() // 1_000_000,
                image_file=snapshot.meta.image_file, optical_file=snapshot.meta.optical_file,
                valid_points=snapshot.meta.valid_points, capture_fps=snapshot.meta.capture_fps,
                tracks=tuple(item.track for item in state.items if item.observed_ns == observed_ns))
            pending = directory / "tracking.next.json"
            pending.write_text(output.model_dump_json(), encoding="utf8")
            pending.chmod(0o600)
            pending.replace(directory / "tracking.json")
            if last_sequence % 30 <= 2:
                print(f"vision sequence={last_sequence} tracks={[(item.track.id, item.track.kind) for item in state.items if item.observed_ns == observed_ns]}", flush=True)


if __name__ == "__main__":
    typer.run(main)
