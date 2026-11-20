"""Independent analytic pinhole/Brown fixtures, with no production geometry calls."""

import hashlib
import math
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from calibration_models import CalibrationInput, Frame


def rotation(angles: tuple[float, float, float]) -> NDArray[np.float64]:
    x, y, z = map(math.radians, angles)
    rx = np.array(
        [[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]]
    )
    ry = np.array(
        [[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]]
    )
    rz = np.array(
        [[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]]
    )
    return np.asarray(rz @ ry @ rx, dtype=np.float64)


def scene(view: int = 0) -> CalibrationInput:
    """Generate two camera orientations; elevated target also changes yaw/position."""
    corners = np.array(
        [[-20, -20, 0], [20, -20, 0], [20, 20, 0], [-20, 20, 0]], dtype=float
    )
    camera_rotation = rotation((12, -18, 5) if view == 0 else (-8, 8, -12))
    camera_translation = np.array([-60, -60, 600.0 if view == 0 else 640.0])

    def project(points: NDArray[np.float64]) -> list[list[float]]:
        normalized = points[:, :2] / points[:, 2:]
        x, y = normalized[:, 0], normalized[:, 1]
        r2 = x * x + y * y
        radial = 1 - 0.18 * r2 + 0.04 * r2 * r2 - 0.006 * r2 * r2 * r2
        u = 580 * (x * radial + 0.002 * x * y - 0.001 * (r2 + 2 * x * x)) + 318
        v = 575 * (y * radial + 0.001 * (r2 + 2 * y * y) - 0.002 * x * y) + 241
        return np.column_stack((u, v)).tolist()

    def frame(
        angles: tuple[float, float, float] | None,
        target: tuple[float, float, float, float],
    ) -> Frame:
        matrix = camera_rotation if angles is None else rotation(angles)
        translation = (
            camera_translation
            if angles is None
            else np.array([-60, -60, 430.0 + angles[0]])
        )
        markers = []
        for marker_id, center in enumerate(
            ((0, 0, 0), (120, 0, 0), (120, 120, 0), (0, 120, 0))
        ):
            markers.append(
                {
                    "marker_id": marker_id,
                    "corners": project((corners + center) @ matrix.T + translation),
                }
            )
        x, y, z, yaw = target
        target_points = corners @ rotation((0, 0, yaw)).T + [x, y, z]
        markers.append(
            {
                "marker_id": 10,
                "corners": project(target_points @ matrix.T + translation),
            }
        )
        return Frame.model_validate(
            {
                "markers": markers,
                "captured_ms": 10000,
                "camera_revision": "camera-a" if view == 0 else "camera-b",
                "reference_revision": "board-v1",
                "boundary_visible": True,
                "all_feet_visible": True,
                "contact_label": "contact",
            }
        )

    poses = ((55, 55, -65, 0), (70, 45, -65, 15), (45, 65, -65, -20))
    views = [
        frame((x, y, z), poses[0])
        for x, y, z in (
            (-25, -20, -10),
            (25, -20, 10),
            (-20, 25, 15),
            (25, 25, -15),
            (10, -30, 0),
            (-30, 10, 20),
            (15, 15, 30),
            (-15, -15, -25),
            (30, 5, -20),
            (5, 30, 10),
        )
    ]
    return CalibrationInput.model_validate(
        {
            "schema_version": 1,
            "provenance": "synthetic",
            "camera": "Logitech Webcam C930e",
            "image_size": [640, 480],
            "fps": 15,
            "pixel_format": "yuyv422",
            "camera_revision": "camera-a" if view == 0 else "camera-b",
            "reference_revision": "board-v1",
            "stage_id": "fixture-stage",
            "measured_reference_side_mm": 40,
            "measured_target_side_mm": 40,
            "measured_baseline_mm": 120,
            "minimum_translation_mm": 25,
            "minimum_yaw_deg": 10,
            "measurement_uncertainty_mm": 0.5,
            "measurement_uncertainty_deg": 0.2,
            "containment_verified": True,
            "setup": "clearance",
            "intrinsic_views": views,
            "reference": frame(None, poses[0]),
            "validations": [
                {
                    "frame": frame(None, pose),
                    "expected": dict(
                        zip(("x_mm", "y_mm", "z_mm", "yaw_deg"), pose, strict=True)
                    ),
                }
                for pose in poses
            ],
            "current": frame(None, poses[-1]),
        }
    )


def raster(frame: Frame) -> NDArray[np.uint8]:
    """Render independently projected image corners as supersampled actual tags."""

    canvas = np.full((480 * 4, 640 * 4), 255, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    source = np.array([[0, 0], [239, 0], [239, 239], [0, 239]], dtype=np.float32)
    for marker in frame.markers:
        tag = cv2.aruco.generateImageMarker(dictionary, marker.marker_id, 240)
        transform = cv2.getPerspectiveTransform(
            source, np.array(marker.corners, dtype=np.float32) * 4
        )
        warped = cv2.warpPerspective(tag, transform, (2560, 1920), borderValue=(255,))
        canvas = np.minimum(canvas, warped)
    return np.asarray(
        cv2.resize(canvas, (640, 480), interpolation=cv2.INTER_AREA), dtype=np.uint8
    )


def image_scene(directory: Path, view: int) -> CalibrationInput:
    """Write a complete synthetic image replay with fresh per-image digest binding."""
    data = scene(view)

    def save(frame: Frame, name: str) -> Frame:
        path = directory / f"camera-{view}-{name}.png"
        if not cv2.imwrite(str(path), raster(frame)):
            message = "fixture image write failed"
            raise RuntimeError(message)
        return frame.model_copy(
            update={
                "image_file": path.name,
                "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    views = [
        save(
            frame.model_copy(
                update={"markers": tuple(m for m in frame.markers if m.marker_id != 10)}
            ),
            f"intrinsic-{i}",
        )
        for i, frame in enumerate(data.intrinsic_views)
    ]
    return CalibrationInput.model_validate(
        data.model_dump()
        | {
            "intrinsic_views": views,
            "reference": save(data.reference, "reference"),
            "current": save(data.current, "current"),
            "validations": [
                item.model_dump() | {"frame": save(item.frame, f"validation-{i}")}
                for i, item in enumerate(data.validations)
            ],
        }
    )
