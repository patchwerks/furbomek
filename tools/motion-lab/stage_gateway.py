"""Trusted local stage DTOs and pure geometry; no device adapter imports."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "services/embodiment-gateway/src")
)

from furbomek_gateway.motion_geometry import Polygon, Transform
from furbomek_gateway.stage_admission import verify_stage
from furbomek_gateway.stage_models import (
    ContainmentCheck,
    StageReceipt,
    StageRequest,
    StageSurvey,
)

__all__ = [
    "ContainmentCheck",
    "Polygon",
    "StageReceipt",
    "StageRequest",
    "StageSurvey",
    "Transform",
    "verify_stage",
]
