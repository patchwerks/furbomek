"""Bounded image import and video-only C930e capture; no control surfaces."""

import hashlib
import subprocess
import time
from pathlib import Path
from typing import assert_never

import cv2

from calibration_geometry import CalibrationHoldError
from calibration_models import CalibrationInput, Frame, Marker


def detect_frame(path: Path, reference: Frame) -> Frame:
    """Decode actual image tags; explicit visibility labels remain operator evidence."""
    image = cv2.imread(str(path))
    if image is None or image.shape[:2] != (480, 640):
        raise CalibrationHoldError("unreadable_or_wrong_image_mode")
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), parameters
    )
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None:
        raise CalibrationHoldError("no_decoded_tags")
    markers = tuple(
        Marker.model_validate(
            {"marker_id": int(marker_id[0]), "corners": points.reshape(4, 2).tolist()}
        )
        for marker_id, points in zip(ids, corners, strict=True)
    )
    return Frame.model_validate(
        reference.model_dump()
        | {
            "markers": [marker.model_dump() for marker in markers],
        }
    )


def capture_current(directory: Path, reference: Frame) -> Frame:
    """Read exactly one C930e frame; subprocess timeout bounds unavailable cameras."""
    path = directory / "current.png"
    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-f",
        "avfoundation",
        "-framerate",
        "15",
        "-video_size",
        "640x480",
        "-pixel_format",
        "yuyv422",
        "-i",
        "Logitech Webcam C930e:none",
        "-an",
        "-frames:v",
        "1",
        str(path),
    ]
    try:
        with (directory / "capture.log").open("wb") as log:
            _ = subprocess.run(command, stdout=log, stderr=log, check=True, timeout=15)
    except (subprocess.SubprocessError, FileNotFoundError) as error:
        raise CalibrationHoldError("camera_capture_failed") from error
    fresh = reference.model_copy(
        update={
            "captured_ms": int(time.time() * 1000),
            "boundary_visible": False,
            "all_feet_visible": False,
            "contact_label": "unknown",
            "image_file": path.name,
            "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    return detect_frame(path, fresh)


def import_images(data: CalibrationInput, directory: Path) -> CalibrationInput:
    """Measured imports decode hash-bound files instead of trusting pasted corners."""
    match data.provenance:
        case "synthetic":
            if data.reference.image_file is None:
                return data
        case "measured":
            pass
        case unreachable:
            assert_never(unreachable)

    def read(frame: Frame) -> Frame:
        if frame.image_file is None or frame.image_sha256 is None:
            raise CalibrationHoldError("measured_image_provenance_missing")
        path = directory / frame.image_file
        if (
            path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != frame.image_sha256
        ):
            raise CalibrationHoldError("image_digest_mismatch")
        return detect_frame(path, frame)

    return CalibrationInput.model_validate(
        data.model_dump()
        | {
            "intrinsic_views": [
                read(frame).model_dump() for frame in data.intrinsic_views
            ],
            "reference": read(data.reference).model_dump(),
            "validations": [
                item.model_dump() | {"frame": read(item.frame).model_dump()}
                for item in data.validations
            ],
            "current": read(data.current).model_dump(),
        }
    )
