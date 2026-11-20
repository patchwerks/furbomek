"""Metric board correspondences and 3D pose recovery, never floor homography."""

from dataclasses import dataclass
from typing import Final, override

import cv2
import numpy as np
from numpy.typing import NDArray

from calibration_models import Frame, Pose

REFERENCE_SIDE_MM: Final = 40.0
TARGET_SIDE_MM: Final = 40.0
BASELINE_MM: Final = 120.0
REFERENCE_CENTERS: Final = {
    0: (0.0, 0.0),
    1: (120.0, 0.0),
    2: (120.0, 120.0),
    3: (0.0, 120.0),
}
TARGET_ID: Final = 10
Array = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class CalibrationHoldError(Exception):
    """Named rejection carried to the CLI receipt."""

    reason: str

    @override
    def __str__(self) -> str:
        """Expose the stable machine reason."""
        return self.reason


@dataclass(frozen=True, slots=True)
class Lens:
    """Fitted pinhole camera with five radial/tangential distortion terms."""

    matrix: Array
    distortion: Array
    rms: float


def square(side: float) -> Array:
    """Counterpart of ArUco's clockwise image corners in board x-right/y-down."""
    half = side / 2
    return np.array(
        [[-half, -half, 0], [half, -half, 0], [half, half, 0], [-half, half, 0]],
        dtype=np.float64,
    )


def reference_points() -> Array:
    """Four printed tags with two independently measurable 120 mm baselines."""
    return np.concatenate(
        [
            square(REFERENCE_SIDE_MM) + np.array([x, y, 0], dtype=np.float64)
            for x, y in REFERENCE_CENTERS.values()
        ]
    )


def image_points(frame: Frame, ids: tuple[int, ...]) -> Array:
    """Require complete unique decodes and a visible image border."""
    markers = {marker.marker_id: marker for marker in frame.markers}
    if len(markers) != len(frame.markers) or any(
        marker_id not in markers for marker_id in ids
    ):
        raise CalibrationHoldError("missing_or_duplicate_markers")
    points = np.array(
        [corner for marker_id in ids for corner in markers[marker_id].corners],
        dtype=np.float64,
    )
    if np.any(points < 2) or np.any(points[:, 0] >= 638) or np.any(points[:, 1] >= 478):
        raise CalibrationHoldError("cropped_marker")
    for marker_id in ids:
        area = cv2.contourArea(np.array(markers[marker_id].corners, dtype=np.float32))
        if area < 100:
            raise CalibrationHoldError("insufficient_marker_resolution")
    return points


def recover_lens(views: tuple[Frame, ...]) -> Lens:
    """Fit only diverse intrinsic views; held-out survey poses remain independent."""
    pixels = [image_points(frame, (0, 1, 2, 3)) for frame in views]
    normalized = np.array([(p - p.mean(axis=0)).flatten() for p in pixels])
    if (
        float(np.linalg.svd(normalized - normalized.mean(axis=0), compute_uv=False)[2])
        < 2
    ):
        raise CalibrationHoldError("insufficient_intrinsic_view_diversity")
    objects = [reference_points().astype(np.float32) for _ in pixels]
    rms, matrix, distortion, _, _ = cv2.calibrateCamera(
        objects,
        [p.astype(np.float32) for p in pixels],
        (640, 480),
        np.eye(3, dtype=np.float64),
        np.zeros(5, dtype=np.float64),
    )
    if not np.isfinite(matrix).all() or not np.isfinite(distortion).all() or rms > 1.0:
        raise CalibrationHoldError("intrinsic_residual")
    return Lens(
        np.asarray(matrix, dtype=np.float64),
        np.asarray(distortion, dtype=np.float64),
        float(rms),
    )


def camera_pose(points: tuple[Array, Array], lens: Lens) -> tuple[Array, Array]:
    """Recover object-to-camera extrinsics with positive depth and residual gates."""
    objects, pixels = points
    ok, rotation, translation = cv2.solvePnP(
        objects, pixels, lens.matrix, lens.distortion, flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not ok:
        raise CalibrationHoldError("pose_solver_failed")
    matrix, _ = cv2.Rodrigues(rotation)
    depths = (matrix @ objects.T + translation)[2]
    predicted, _ = cv2.projectPoints(
        objects, rotation, translation, lens.matrix, lens.distortion
    )
    residual = np.linalg.norm(predicted.reshape(-1, 2) - pixels, axis=1)
    if np.any(depths <= 0) or float(residual.max()) > 1.0:
        raise CalibrationHoldError("pose_residual")
    return np.asarray(matrix, dtype=np.float64), np.asarray(
        translation, dtype=np.float64
    )


def target_pose(frame: Frame, lens: Lens, site: tuple[Array, Array]) -> Pose:
    """Compose target-to-camera with camera-to-reference, retaining target height."""
    target_rotation, target_translation = camera_pose(
        (square(TARGET_SIDE_MM), image_points(frame, (TARGET_ID,))), lens
    )
    reference_rotation, reference_translation = site
    rotation = reference_rotation.T @ target_rotation
    position = (
        reference_rotation.T @ (target_translation - reference_translation)
    ).flatten()
    tilt = float(np.rad2deg(np.arccos(np.clip(rotation[2, 2], -1, 1))))
    if tilt > 10:
        raise CalibrationHoldError("target_not_rigid_parallel_to_stage")
    return Pose(
        x_mm=float(position[0]),
        y_mm=float(position[1]),
        z_mm=float(position[2]),
        yaw_deg=float(np.rad2deg(np.arctan2(rotation[1, 0], rotation[0, 0]))),
    )
