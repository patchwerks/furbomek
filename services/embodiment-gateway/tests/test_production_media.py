"""Real consumer observations, not fabricated positive receipts."""

from pathlib import Path

import pytest

from furbomek_gateway.production_mailbox import PrivateMailbox
from furbomek_gateway.production_media import ProductionMedia
from furbomek_gateway.production_media_contracts import VisualSettings
from furbomek_gateway.reaction_types import AdapterFaultError

from .production_media_support import dispatch, eventually, media

__all__ = ["media"]


def test_dispatch_waits_for_exact_real_consumer_and_restores(
    media: ProductionMedia,
) -> None:
    request = dispatch(media)
    media.dispatch(request)
    ack = eventually(
        lambda: media.acknowledge(request.owner), lambda value: value is not None
    )
    assert ack is not None
    assert ack.revision == request.previous.revision + 1
    assert media.snapshot("graphics").effect == request.cue.effect
    assert media.release(media.snapshot("graphics"), request.previous)
    assert media.renderer().look == "rgb.fixed.v1"
    assert media.renderer().owner == ""


def test_manual_override_revokes_lease_and_stale_restore(
    media: ProductionMedia,
) -> None:
    request = dispatch(media)
    media.dispatch(request)
    _ = eventually(
        lambda: media.acknowledge(request.owner), lambda value: value is not None
    )
    state = media.snapshot("graphics")
    _ = (media.mailbox.directory / "fixture-manual").write_text("manual")
    _ = eventually(lambda: media.renderer().owner, lambda value: value == "operator")
    assert media.acknowledge(request.owner) is None
    assert not media.release(state, request.previous)
    media.stop()
    assert media.renderer().owner == "operator"


def test_visual_settings_apply_actual_bounded_orbit(media: ProductionMedia) -> None:
    settings = VisualSettings(
        look="xyz.crimson.v1",
        point_pixels=3.0,
        zoom=1.4,
        yaw=0.4,
        pitch=-0.2,
        hud_visible=False,
    )
    owner = media.apply_visual(settings, media.snapshot("graphics"), duration_ms=1500)
    receipt = eventually(
        lambda: media.visual_receipt(owner), lambda value: value is not None
    )
    assert receipt is not None
    assert receipt.look == "xyz.crimson.v1"
    assert receipt.effective is not None
    assert receipt.effective.yaw == 0.4
    assert receipt.effective.hud_visible is False
    assert receipt.effective.duration_ms == 1500


def test_revision_mismatch_is_rejected_before_write(media: ProductionMedia) -> None:
    request = dispatch(media)
    stale = request.model_copy(
        update={"previous": request.previous.model_copy(update={"revision": 8})}
    )
    with pytest.raises(AdapterFaultError):
        media.dispatch(stale)
    assert not (media.mailbox.directory / "effects.json").exists()


def test_uninstalled_sfx_and_nonmedia_are_unavailable(media: ProductionMedia) -> None:
    assert not media.available("sfx")
    assert not media.available("hud")
    assert not media.available("robot")


def test_mailbox_excludes_competing_writers_and_symlink_receipts(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        with pytest.raises(BlockingIOError), PrivateMailbox(tmp_path):
            pytest.fail("second writer acquired the mailbox")
        (tmp_path / "effects-ack.json").symlink_to(tmp_path / "production-media.lock")
        with pytest.raises(OSError, match=r"Too many levels|symbolic links"):
            _ = mailbox.read("effects-ack.json")


def test_restoration_keeps_prior_visual_parameters_and_clears_owner(
    media: ProductionMedia,
) -> None:
    settings = VisualSettings(look="xyz.crimson.v1", point_pixels=2.8, yaw=0.3)
    token = media.apply_visual(settings, media.snapshot("graphics"))
    _ = eventually(lambda: media.visual_receipt(token), lambda value: value is not None)
    request = dispatch(media)
    media.dispatch(request)
    _ = eventually(
        lambda: media.acknowledge(request.owner), lambda value: value is not None
    )
    assert media.release(media.snapshot("graphics"), request.previous)
    receipt = media.renderer()
    assert receipt.owner == ""
    assert receipt.look == "xyz.crimson.v1"
    assert receipt.effective is not None
    assert receipt.effective.point_pixels == 2.8
    assert receipt.effective.yaw == 0.3
