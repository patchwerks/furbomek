"""Bounded, acknowledged lease restoration; no optimistic release."""

from __future__ import annotations

from time import monotonic, sleep
from typing import TYPE_CHECKING

from .production_media_contracts import SfxRequest

if TYPE_CHECKING:
    from .production_media_channel import MediaChannel
    from .reaction_types import PropertyState


def release_graphics(
    channel: MediaChannel, state: PropertyState, previous: PropertyState | None
) -> bool:
    """Restore only recorded values under the exact current owner/revision."""
    receipt = channel.renderer()
    if (
        receipt.actor_id != channel.binding.actor_id
        or receipt.owner != state.owner
        or receipt.revision != state.revision
        or receipt.effective is None
    ):
        return False
    restore = channel.observed.get(previous.revision) if previous else None
    if previous is not None and previous.effect is not None and restore is None:
        return False
    wire = (restore or receipt.effective).model_copy(
        update={
            "expected_owner": receipt.owner,
            "expected_revision": receipt.revision,
            "revision": receipt.revision + 1,
            "issued_ms": channel.clock.epoch_ms(),
            "actor_id": channel.binding.actor_id,
            "operation": "release" if restore else "stop",
        }
    )
    channel.mailbox.write("effects.json", wire.model_dump_json())
    until = monotonic() + 0.5
    while monotonic() < until:
        observed = channel.renderer()
        if observed.consumer_id != receipt.consumer_id:
            return False
        if observed.revision == wire.revision:
            return (
                observed.status in {"applied", "stopped"}
                and observed.owner == ""
                and (
                    observed.effective == wire
                    if restore
                    else observed.effective is None
                )
            )
        sleep(0.01)
    return False


def release_audio(channel: MediaChannel, state: PropertyState) -> bool:
    """CAS-stop audio without replaying a previous one-shot sound."""
    receipt = channel.audio()
    if (
        receipt.actor_id != channel.binding.actor_id
        or receipt.owner != state.owner
        or receipt.revision != state.revision
    ):
        return False
    wire = SfxRequest(
        consumer_id=receipt.consumer_id,
        actor_id=channel.binding.actor_id,
        cue_id=receipt.cue_id,
        owner=receipt.owner,
        expected_owner=receipt.owner,
        expected_revision=receipt.revision,
        revision=receipt.revision + 1,
        issued_ms=channel.clock.epoch_ms() // 1000 * 1000,
        duration_ms=receipt.duration_ms,
        preset=receipt.preset,
        gain_percent=receipt.gain_percent,
        operation="stop",
    )
    channel.mailbox.write("sfx.json", wire.model_dump_json())
    until = monotonic() + 0.5
    while monotonic() < until:
        current = channel.audio()
        if current.revision == wire.revision:
            return current.status == "stopped" and current.owner == ""
        sleep(0.01)
    return False
