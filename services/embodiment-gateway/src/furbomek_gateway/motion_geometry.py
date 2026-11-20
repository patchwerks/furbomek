"""Finite millimeter geometry for surveyed convex stage regions."""

from math import cos, radians, sin
from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type Finite = Annotated[float, Field(allow_inf_nan=False, strict=True, ge=-1e9, le=1e9)]
type Nonnegative = Annotated[Finite, Field(ge=0)]
type Positive = Annotated[Finite, Field(gt=0)]
type Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")]
type Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
type Point = tuple[Finite, Finite]


class Contract(BaseModel):
    """Closed immutable boundary; mutable copies must be parsed again."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class MotionContractError(ValueError):
    """A geometric or measurement invariant was violated."""


class Transform(Contract):
    """Rigid planar transform: rotate counterclockwise, then translate."""

    x_mm: Finite
    y_mm: Finite
    yaw_deg: Annotated[Finite, Field(ge=-180, le=180)]

    def apply(self, point: Point) -> Point:
        """Map an observation-frame point into the anchored stage frame."""
        angle = radians(self.yaw_deg)
        return (
            self.x_mm + cos(angle) * point[0] - sin(angle) * point[1],
            self.y_mm + sin(angle) * point[0] + cos(angle) * point[1],
        )


def cross(a: Point, b: Point, c: Point) -> float:
    """Return signed twice-area, positive to the left of the edge."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


class Polygon(Contract):
    """Strict convex counterclockwise polygon; concave surveys need subdivision."""

    vertices: Annotated[tuple[Point, ...], Field(min_length=3, max_length=128)]

    @model_validator(mode="after")
    def convex(self) -> Self:
        """Reject degeneracy, crossing edges, repeats and clockwise winding."""
        for i, a in enumerate(self.vertices):
            b = self.vertices[(i + 1) % len(self.vertices)]
            for j, c in enumerate(self.vertices):
                if j not in (i, (i + 1) % len(self.vertices)) and cross(a, b, c) <= 0:
                    msg = "polygon_requires_strict_convex_ccw"
                    raise MotionContractError(msg)
        return self

    def contains(self, point: Point) -> bool:
        """Include the surveyed boundary without numerical widening."""
        return all(
            cross(a, self.vertices[(i + 1) % len(self.vertices)], point) >= 0
            for i, a in enumerate(self.vertices)
        )


class SurfaceClass(Contract):
    """Measured uncertainty-inclusive intervals for a specific material/finish."""

    material_id: Identifier
    finish_id: Identifier
    slope_deg: tuple[Nonnegative, Nonnegative]
    static_traction: tuple[Nonnegative, Nonnegative]
    traction_units: Literal["coefficient"] = "coefficient"

    @model_validator(mode="after")
    def ordered(self) -> Self:
        """Require ordered measured intervals."""
        if (
            self.slope_deg[0] > self.slope_deg[1]
            or self.static_traction[0] > self.static_traction[1]
        ):
            msg = "reversed_surface_interval"
            raise MotionContractError(msg)
        return self

    def covers(self, measured: Self) -> bool:
        """Allow reuse only within tested material and interval bounds."""
        return (
            self.material_id == measured.material_id
            and self.finish_id == measured.finish_id
            and self.slope_deg[0]
            <= measured.slope_deg[0]
            <= measured.slope_deg[1]
            <= self.slope_deg[1]
            and self.static_traction[0]
            <= measured.static_traction[0]
            <= measured.static_traction[1]
            <= self.static_traction[1]
        )
