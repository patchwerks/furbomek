"""Submission and missing/muted audio stay HOLD; no playback is fabricated."""

from pathlib import Path

import pytest

from furbomek_gateway.effect_contracts import SfxEffect
from furbomek_gateway.production_mailbox import PrivateMailbox
from furbomek_gateway.production_media import ProductionMedia
from furbomek_gateway.production_media_channel import MediaBinding
from furbomek_gateway.production_media_contracts import SfxReceipt, SfxRequest
from furbomek_gateway.reaction_contracts import Cue
from furbomek_gateway.reaction_types import Dispatch, HostClock


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("muted", [False, True])
def test_audio_requires_explicit_local_enable_and_unmuted_receipt(
    tmp_path: Path,
    *,
    enabled: bool,
    muted: bool,
) -> None:
    clock = HostClock()
    tmp_path.chmod(0o700)
    initial = SfxReceipt(
        schema_version="furbomek.sfx-ack.v1",
        consumer_id="audio",
        actor_id="",
        status="ready",
        owner="",
        cue_id="",
        revision=0,
        muted=muted,
        source_available=True,
        published_ms=clock.epoch_ms(),
        preset="acknowledge",
        gain_percent=0,
        duration_ms=3000,
    )
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("sfx-ack.json", initial.model_dump_json())
        adapter = ProductionMedia(
            mailbox, clock, MediaBinding("actor", sfx_enabled=enabled)
        )
        assert adapter.available("sfx") == (enabled and not muted)


def test_submitted_audio_is_not_applied_and_stop_survives_missing_renderer(
    tmp_path: Path,
) -> None:
    clock = HostClock()
    tmp_path.chmod(0o700)
    receipt = SfxReceipt(
        schema_version="furbomek.sfx-ack.v1",
        consumer_id="audio",
        actor_id="",
        status="ready",
        owner="",
        cue_id="",
        revision=0,
        muted=False,
        source_available=True,
        published_ms=clock.epoch_ms(),
        preset="acknowledge",
        gain_percent=0,
        duration_ms=3000,
    )
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("sfx-ack.json", receipt.model_dump_json())
        adapter = ProductionMedia(
            mailbox, clock, MediaBinding("actor", sfx_enabled=True)
        )
        effect = SfxEffect(
            capability="sfx.preset.v1",
            preset="acknowledge",
            gain_percent=30,
            duration_ms=3000,
        )
        cue = Cue(
            id="audio-cue",
            after=(),
            effect=effect,
            condition="always",
            ttl_ms=3000,
            on_unavailable="skip",
            on_fault="cancel_pack",
        )
        request = Dispatch(
            owner="audio-owner",
            cue=cue,
            resource="sfx",
            previous=adapter.snapshot("sfx"),
            deadline_ms=clock.monotonic_ms() + 1000,
        )
        adapter.dispatch(request)
        wire = SfxRequest.model_validate_json(mailbox.read("sfx.json"))
        assert wire.preset == "acknowledge"
        assert wire.operation == "apply"
        submitted = receipt.model_copy(
            update={
                "status": "submitted",
                "owner": request.owner,
                "actor_id": "actor",
                "cue_id": cue.id,
                "revision": 1,
                "gain_percent": 30,
            }
        )
        mailbox.write("sfx-ack.json", submitted.model_dump_json())
        assert adapter.acknowledge(request.owner) is None
        adapter.stop()
        stopped = SfxRequest.model_validate_json(mailbox.read("sfx.json"))
        assert stopped.operation == "stop"
        assert stopped.expected_owner == "audio-owner"
        assert stopped.expected_revision == 1
