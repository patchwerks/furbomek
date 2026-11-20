"""Private calibration import boundary; all lengths are millimetres."""

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

Finite = Annotated[float, Field(allow_inf_nan=False)]
Positive = Annotated[Finite, Field(gt=0)]
Point2 = tuple[Finite, Finite]
Point3 = tuple[Finite, Finite, Finite]
Corners = tuple[Point2, Point2, Point2, Point2]


class Contract(BaseModel):
    """Immutable, closed input contract."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class Marker(Contract):
    """Decoded clockwise corners, starting at marker top left."""

    marker_id: Annotated[int, Field(ge=0, lt=50, strict=True)]
    corners: Corners


class Frame(Contract):
    """Private detector output bound to a view and capture timestamp."""

    image_file: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]+\.png$")] | None = None
    image_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    markers: tuple[Marker, ...]
    captured_ms: Annotated[int, Field(ge=0, strict=True)]
    camera_revision: str
    reference_revision: str
    boundary_visible: bool
    all_feet_visible: bool
    contact_label: Literal["unknown", "supported", "contact", "airborne"]


class Pose(Contract):
    """Independent surveyed chassis target position in the reference frame."""

    x_mm: Finite
    y_mm: Finite
    z_mm: Finite
    yaw_deg: Finite


class ValidationPose(Contract):
    """Held-out target observation paired with an independent survey."""

    frame: Frame
    expected: Pose


class CalibrationInput(Contract):
    """One fixed site plus diverse board views for intrinsic recovery."""

    schema_version: Literal[1]
    provenance: Literal["synthetic", "measured"]
    camera: Literal["Logitech Webcam C930e"]
    image_size: tuple[Literal[640], Literal[480]]
    fps: Literal[15]
    pixel_format: Literal["yuyv422"]
    camera_revision: Annotated[str, Field(min_length=1)]
    reference_revision: Annotated[str, Field(min_length=1)]
    stage_id: Annotated[str, Field(min_length=1)]
    measured_reference_side_mm: Positive
    measured_target_side_mm: Positive
    measured_baseline_mm: Positive
    minimum_translation_mm: Positive
    minimum_yaw_deg: Positive
    measurement_uncertainty_mm: Positive
    measurement_uncertainty_deg: Positive
    containment_verified: bool
    setup: Literal["clearance", "rear_diagnostic"]
    intrinsic_views: Annotated[tuple[Frame, ...], Field(min_length=8)]
    reference: Frame
    validations: Annotated[tuple[ValidationPose, ...], Field(min_length=3)]
    current: Frame
    maximum_age_ms: Annotated[int, Field(gt=0, le=600, strict=True)] = 600


class CalibrationResult(Contract):
    """Replay and physical results cannot silently become motion admission."""

    schema_version: Literal[1] = 1
    status: Literal["HOLD", "CALIBRATED_REPLAY", "CALIBRATED_OBSERVATION"]
    reasons: tuple[str, ...] = ()
    motion_admitted: Literal[False] = False
    provenance: Literal["synthetic", "measured", "unavailable"]
    translation_error_mm: float | None = None
    yaw_error_deg: float | None = None
    intrinsic_rms_px: float | None = None
    camera_matrix: tuple[tuple[float, ...], ...] | None = None
    distortion: tuple[float, ...] | None = None
    recovered_poses: tuple[Pose, ...] = ()
    input_sha256: str | None = None
    stage_id: str | None = None
    camera_revision: str | None = None
    reference_revision: str | None = None
    reference_to_camera_rotation: tuple[tuple[float, ...], ...] | None = None
    reference_to_camera_translation_mm: tuple[float, ...] | None = None
