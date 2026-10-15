from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from numpy.typing import NDArray
from vision_frames import Snapshot, TargetKind, Track


@dataclass(frozen=True, slots=True)
class Candidate:
    kind: TargetKind
    bounds: tuple[float, float, float, float]
    score: float
    landmarks: tuple[tuple[float, float], ...] = ()
    pixel_mask: NDArray[np.uint8] | None = None


def make_track(snapshot: Snapshot, candidate: Candidate) -> Track | None:
    left, top, right, bottom = candidate.bounds
    x0, y0 = max(0, int(left * 512)), max(0, int(top * 424))
    x1, y1 = min(512, int(right * 512)), min(424, int(bottom * 424))
    if x1 <= x0 or y1 <= y0:
        return None
    grid = snapshot.points[y0:y1, x0:x1]
    valid = grid[:, :, 15] > 0
    if candidate.pixel_mask is not None:
        valid &= candidate.pixel_mask[y0:y1, x0:x1] > 0
    xyz = grid[:, :, [3, 7, 11]][valid]
    if len(xyz) < 12:
        return None
    near = np.percentile(-xyz[:, 2], 35)
    foreground = xyz[(-xyz[:, 2] >= near - 0.25) & (-xyz[:, 2] <= near + 0.25)]
    if len(foreground) < 12:
        return None
    low, high = np.min(foreground, axis=0), np.max(foreground, axis=0)
    rows, columns = np.nonzero(valid)
    samples = np.unique(np.concatenate((np.linspace(0, len(xyz) - 1, 56, dtype=np.int32),
        np.array([np.argmin(rows), np.argmax(rows), np.argmin(columns), np.argmax(columns)], dtype=np.int32))))
    outline = tuple((float(xyz[index, 0]), float(xyz[index, 1]), float(xyz[index, 2])) for index in samples)
    roi_map = snapshot.color_map[y0:y1, x0:x1]
    paired = valid & (roi_map >= 0) & (roi_map < 1920 * 1080)
    probe_rows, probe_columns = np.nonzero(paired if np.any(paired) else valid)
    nearest = int(np.argmin((probe_rows - (y1 - y0) / 2) ** 2 + (probe_columns - (x1 - x0) / 2) ** 2))
    probe = grid[probe_rows[nearest], probe_columns[nearest]]
    probe_map = int(roi_map[probe_rows[nearest], probe_columns[nearest]])
    probe_optical = (probe_map % 1920 / 1920, probe_map // 1920 / 1080) if 0 <= probe_map < 1920 * 1080 else None
    mapped = snapshot.color_map[y0:y1, x0:x1][valid]
    mapped = mapped[(mapped >= 0) & (mapped < 1920 * 1080)]
    optical: tuple[float, float, float, float] | None = None
    if len(mapped):
        u, v = mapped % 1920 / 1920, mapped // 1920 / 1080
        match candidate.kind:
            case "object":
                xlo, xhi = np.quantile(u, (0.025, 0.975))
                ylo, yhi = np.quantile(v, (0.025, 0.975))
            case "body" | "face" | "surface":
                xlo, xhi, ylo, yhi = np.min(u), np.max(u), np.min(v), np.max(v)
            case unreachable:
                assert_never(unreachable)
        optical = (float(xlo), float(ylo), float(xhi - xlo), float(yhi - ylo))
    names = {"body": "BODY ACQUIRED", "face": "FACE LOCK", "surface": "SURFACE TRACK", "object": "FURB-O-MEK / VISUAL TRACK"}
    scores = {"body": "pose_visibility", "face": "face_confidence", "surface": "depth_occupancy", "object": "orb_inlier_ratio"}
    return Track(kind=candidate.kind, label=names[candidate.kind], box=(x0 / 512, y0 / 424, (x1 - x0) / 512,
                 (y1 - y0) / 424), optical_box=optical,
                 world_box=(float(low[0]), float(low[1]), float(low[2]), float(high[0]), float(high[1]), float(high[2])),
                 world_outline=outline,
                 probe_world=(float(probe[3]), float(probe[7]), float(probe[11])),
                 probe_pixel=((x0 + int(probe_columns[nearest])) / 512, (y0 + int(probe_rows[nearest])) / 424),
                 probe_optical=probe_optical,
                 score=candidate.score, score_type=scores[candidate.kind],
                 landmarks=candidate.landmarks)


def detect(snapshot: Snapshot, models: tuple[vision.PoseLandmarker, vision.FaceDetector], template: Path) -> tuple[Track, ...]:
    pose, face = models
    image = mp.Image(image_format=mp.ImageFormat.SRGB,
                     data=cv2.cvtColor(snapshot.image, cv2.COLOR_BGR2RGB))
    timestamp = snapshot.meta.capture_monotonic_ns // 1_000_000
    poses = pose.detect_for_video(image, timestamp)
    faces = face.detect_for_video(image, timestamp)
    candidates: list[Track] = []
    for landmarks in poses.pose_landmarks:
        visible = [point for point in landmarks if point.visibility is not None and point.visibility >= 0.6]
        if len(visible) < 8:
            continue
        bounds = (min(point.x for point in visible) - 0.04, min(point.y for point in visible) - 0.06,
                  max(point.x for point in visible) + 0.04, max(point.y for point in visible) + 0.04)
        track = make_track(snapshot, Candidate("body", bounds, min(1.0, sum(float(point.visibility or 0) for point in visible) / len(visible))))
        if track:
            candidates.append(track)
    for detection in faces.detections:
        box = detection.bounding_box
        bounds = (box.origin_x / 512, box.origin_y / 424, (box.origin_x + box.width) / 512,
                  (box.origin_y + box.height) / 424)
        landmarks = tuple((point.x, point.y) for point in detection.keypoints or ())
        track = make_track(snapshot, Candidate("face", bounds, detection.categories[0].score, landmarks))
        if track:
            candidates.append(track)
    z = -snapshot.points[:, :, 11]
    valid = snapshot.points[:, :, 15] > 0
    if np.count_nonzero(valid) >= 100:
        threshold = float(np.percentile(z[valid], 12)) + 0.14
        mask: NDArray[np.uint8] = np.array(valid & (z <= threshold), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8))
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        if count > 1:
            component = stats[1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))]
            x, y, width, height, area = (int(value) for value in component)
            if area >= 400 and width >= 16 and height >= 16:
                track = make_track(snapshot, Candidate("surface", (x / 512, y / 424, (x + width) / 512,
                                   (y + height) / 424), min(1.0, area / (width * height))))
                if track:
                    candidates.append(track)
    mask_path = template.with_name("robot-template-mask.png")
    if template.is_file() and mask_path.is_file():
        reference = cv2.imread(str(template), cv2.IMREAD_GRAYSCALE)
        reference_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if reference is None or reference_mask is None or reference_mask.shape != reference.shape:
            raise RuntimeError("Robot template and object mask must be matching grayscale images.")
        orb = cv2.ORB_create(nfeatures=1200, edgeThreshold=5, fastThreshold=7)
        source_keys, source_descriptors = orb.detectAndCompute(reference, reference_mask)
        target_keys, target_descriptors = orb.detectAndCompute(cv2.cvtColor(snapshot.image, cv2.COLOR_BGR2GRAY), None)
        if source_descriptors is not None and target_descriptors is not None:
            matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(source_descriptors, target_descriptors)
            good = [match for match in matches if match.distance < 48]
            if len(good) >= 10:
                source = np.float32([source_keys[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
                target = np.float32([target_keys[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
                homography, inliers = cv2.findHomography(source, target, cv2.RANSAC, 3.0)
                if homography is not None and inliers is not None and np.count_nonzero(inliers) >= 10:
                    height, width = reference.shape
                    corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
                    projected = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
                    lo, hi = np.min(projected, axis=0), np.max(projected, axis=0)
                    if 16 < hi[0] - lo[0] < 400 and 16 < hi[1] - lo[1] < 350:
                        object_mask = cv2.warpPerspective(reference_mask, homography, (512, 424), flags=cv2.INTER_NEAREST)
                        x, y, width, height = cv2.boundingRect(object_mask)
                        track = make_track(snapshot, Candidate("object", (x / 512, y / 424,
                            (x + width) / 512, (y + height) / 424), float(np.mean(inliers)), pixel_mask=object_mask))
                        if track:
                            candidates.append(track)
    return tuple(candidates)


def overlap(left: Track, right: Track) -> float:
    a, b = left.box, right.box
    width = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    intersection = width * height
    return intersection / max(0.00001, a[2] * a[3] + b[2] * b[3] - intersection)


@dataclass(frozen=True, slots=True)
class Identity:
    track: Track
    observed_ns: int


@dataclass(frozen=True, slots=True)
class TrackState:
    items: tuple[Identity, ...] = ()
    next_id: int = 1


def assign_ids(candidates: tuple[Track, ...], state: TrackState, now_ns: int) -> TrackState:
    available = [item for item in state.items if now_ns - item.observed_ns < 600_000_000]
    next_id = state.next_id
    result: list[Identity] = []
    for track in candidates:
        matches = [(overlap(track, old.track), index) for index, old in enumerate(available)
                   if old.track.kind == track.kind]
        best = max(matches, default=(0.0, -1))
        match track.kind:
            case "object":
                identity = "object-furbomek"
                available = [item for item in available if item.track.kind != "object"]
            case "body" | "face" | "surface":
                if best[0] >= 0.15:
                    identity = available.pop(best[1]).track.id
                else:
                    identity = f"{track.kind}-{next_id:02d}"
                    next_id += 1
            case unreachable:
                assert_never(unreachable)
        result.append(Identity(track.model_copy(update={"id": identity}), now_ns))
    return TrackState((*result, *available), next_id)
