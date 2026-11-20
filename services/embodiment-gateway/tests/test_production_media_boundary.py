"""Adversarial private receipt inputs cannot manufacture scheduler success."""

import json
from pathlib import Path

import pytest
from pydantic import JsonValue, ValidationError

from furbomek_gateway.production_mailbox import PrivateMailbox
from furbomek_gateway.production_media import ProductionMedia
from furbomek_gateway.production_media_channel import MediaBinding
from furbomek_gateway.production_media_contracts import (
    RenderReceipt,
    RenderRequest,
    VisualSettings,
)
from furbomek_gateway.reaction_types import HostClock, StorePrivacyError

from .production_media_support import dispatch


def ready(clock: HostClock) -> RenderReceipt:
    return RenderReceipt(
        schema_version="furbomek.effects-ack.v1",
        consumer_id="consumer",
        actor_id="",
        status="ready",
        revision=0,
        owner="",
        cue_id="",
        look="rgb.fixed.v1",
        source_available=True,
        source_sequence=1,
        framing="fixed",
        matched_id="",
        depth_provenance="optical_rgb_no_extra_depth",
        published_ms=clock.epoch_ms(),
        effective=None,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor_id", "foreign"),
        ("consumer_id", "restarted"),
        ("owner", "foreign"),
        ("cue_id", "foreign"),
        ("revision", 2),
        ("look", "xyz.depth.v1"),
        ("published_ms", 1),
        ("source_available", False),
        ("status", "submitted"),
        ("depth_provenance", "native_measured_xyz_512x424"),
        ("capability", "unknown"),
    ],
)
def test_mismatched_receipt_is_never_applied(
    tmp_path: Path, field: str, value: JsonValue
) -> None:
    clock = HostClock()
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        initial = ready(clock)
        mailbox.write("effects-ack.json", initial.model_dump_json())
        adapter = ProductionMedia(mailbox, clock, MediaBinding("actor"))
        request = dispatch(adapter)
        adapter.dispatch(request)
        wire = RenderRequest.model_validate_json(mailbox.read("effects.json"))
        receipt = initial.model_copy(
            update={
                "actor_id": "actor",
                "status": "applied",
                "revision": 1,
                "owner": request.owner,
                "cue_id": request.cue.id,
                "look": wire.look,
                "effective": wire,
            }
        )
        raw = receipt.model_dump(mode="json")
        raw[field] = value
        mailbox.write("effects-ack.json", json.dumps(raw))
        assert adapter.acknowledge(request.owner) is None


@pytest.mark.parametrize(
    "settings",
    [
        '{"look":"arbitrary.shader"}',
        '{"zoom":4}',
        '{"yaw":0.56}',
        '{"point_pixels":10}',
        '{"pulse_hz":1.01}',
        '{"available":true}',
        '{"actor_id":"user"}',
        '{"framing":{}}',
    ],
)
def test_public_visual_controls_reject_authority_or_unbounded_parameters(
    settings: str,
) -> None:
    with pytest.raises(ValidationError):
        _ = VisualSettings.model_validate_json(settings)


def test_mailbox_rejects_shared_directory(tmp_path: Path) -> None:
    tmp_path.chmod(0o755)
    with pytest.raises(StorePrivacyError), PrivateMailbox(tmp_path):
        pytest.fail("shared directory was accepted")
