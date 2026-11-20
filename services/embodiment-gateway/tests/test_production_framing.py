"""Host provenance/clock boundary and real renderer handoff."""

import pytest

from furbomek_gateway.framing_models import Fixed, Frame, Roi, Shot
from furbomek_gateway.production_framing import ProductionFraming
from furbomek_gateway.production_media import ProductionMedia

from .framing_cases import frame, preset
from .production_media_support import dispatch, eventually, media
from .reaction_support import Clock

__all__ = ["media"]


def test_trusted_policy_preserves_lock_loss_hold_and_fixed_fallback() -> None:
    clock = Clock()
    bridge = ProductionFraming(preset(), clock)
    locked = bridge.step(frame(0))
    assert locked.framing.subject_id == "furbomek"
    clock.now = 100
    held = bridge.step(frame(100, robot=False))
    assert held.framing.rules == ("hold",)
    clock.now = 1100
    fallback = bridge.step(frame(1100, robot=False))
    assert fallback.framing.rules == ("fixed",)
    assert fallback.framing.roi == Roi(x=0.0, y=0.0, width=1.0, height=1.0)


@pytest.mark.parametrize("kind", ["stale", "future", "source", "future_signal"])
def test_untrusted_observation_never_changes_policy(kind: str) -> None:
    clock = Clock()
    bridge = ProductionFraming(preset(), clock)
    sample = frame(0)
    if kind == "stale":
        clock.now = 101
    elif kind == "future":
        sample = frame(1)
    else:
        change = {"source": "chat"} if kind == "source" else {"at_ms": 1}
        sample = sample.model_copy(
            update={"signals": (sample.signals[0].model_copy(update=change),)}
        )
    with pytest.raises(ValueError, match=r"clock|provenance"):
        _ = bridge.step(sample)


def test_policy_fixed_roi_reaches_real_consumer_with_short_lived_provenance(
    media: ProductionMedia,
) -> None:
    roi = Roi(x=0.1, y=0.2, width=0.5, height=0.6)
    config = preset().model_copy(
        update={
            "default": "crop",
            "shots": (
                *preset().shots,
                Shot(id="crop", target=Fixed(kind="fixed", roi=roi)),
            ),
        }
    )
    policy = ProductionFraming(config, media.clock)
    selection = policy.step(Frame(now_ms=media.clock.monotonic_ms()))
    media.select_framing(selection)
    request = dispatch(media)
    media.dispatch(request)
    ack = eventually(
        lambda: media.acknowledge(request.owner), lambda value: value is not None
    )
    assert ack is not None
    actual = media.renderer().effective
    assert actual is not None
    assert actual.framing.roi == roi
    assert actual.framing.valid_until_ms > actual.issued_ms
    assert actual.framing.valid_until_ms <= actual.issued_ms + 600
