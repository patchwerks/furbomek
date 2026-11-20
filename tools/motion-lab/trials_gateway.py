"""Trusted monorepo DTO imports; never import device adapters or manifest paths."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "services/embodiment-gateway/src")
)

from furbomek_gateway.guard_models import ActionName
from furbomek_gateway.motion_contracts import MotionProfile, StageProfile, TrialEvidence
from furbomek_gateway.motion_geometry import Polygon, SurfaceClass, Transform, cross

__all__ = [
    "ActionName",
    "MotionProfile",
    "Polygon",
    "StageProfile",
    "SurfaceClass",
    "Transform",
    "TrialEvidence",
    "cross",
]
