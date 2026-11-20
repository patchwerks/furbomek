"""Typed fixtures shared by framing policy scenarios."""

from furbomek_gateway.framing_models import (
    Fixed,
    Frame,
    FramingPreset,
    Roi,
    Rule,
    Shot,
    Signal,
    Subject,
    Trigger,
)

ROBOT = Subject(kind="object", id="furbomek")
PERSON = Subject(kind="person", id="host")


def preset() -> FramingPreset:
    return FramingPreset(
        id="show",
        default="robot",
        fallback="wide",
        tracking_source="tracker",
        shots=(
            Shot(id="robot", target=ROBOT),
            Shot(id="host", target=PERSON),
            Shot(
                id="wide",
                target=Fixed(
                    kind="fixed", roi=Roi(x=0.0, y=0.0, width=1.0, height=1.0)
                ),
            ),
        ),
        rules=(
            Rule(
                id="attention",
                target="host",
                priority=10,
                trigger=Trigger(kind="event", source="broker", subject=PERSON),
            ),
        ),
    )


def frame(now: int, *, event: bool = False, robot: bool = True) -> Frame:
    signals = [
        Signal(
            kind="observation",
            source="tracker",
            subject=PERSON,
            at_ms=now,
            confidence=1.0,
        )
    ]
    if robot:
        signals.append(
            Signal(
                kind="observation",
                source="tracker",
                subject=ROBOT,
                at_ms=now,
                confidence=1.0,
            )
        )
    if event:
        signals.append(
            Signal(
                kind="event", source="broker", subject=PERSON, at_ms=now, confidence=1.0
            )
        )
    return Frame(now_ms=now, signals=tuple(signals))
