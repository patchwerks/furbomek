"""Fresh observed owner state projected without submission or provider data."""

from typing import final

from pydantic import ValidationError

from .effect_contracts import GraphicsEffect, HudEffect, SfxEffect
from .production_effect_owner import EffectOwner
from .production_framing import ProductionFraming
from .production_http_models import OwnerSaved, OwnerState
from .production_media import ProductionMedia
from .production_media_contracts import VisualSettings
from .reaction_types import AdapterFaultError, PropertyState, StorePrivacyError


@final
class OwnerObservation:
    """Track consumer changes to invalidate the controller's shared revision."""

    def __init__(self, media: ProductionMedia, effects: EffectOwner) -> None:
        """No prior receipt is carried across controller restart."""
        self.media = media
        self.effects = effects
        self.seen: PropertyState | None = None

    def read(
        self,
        *,
        epoch: str,
        revision: int,
        saved: OwnerSaved | None,
        framing: ProductionFraming | None,
    ) -> OwnerState:
        """Read actual consumer state and remove stale owner receipts."""
        available = self.media.available("graphics")
        snapshot = None
        visual = None
        if available:
            try:
                snapshot = self.media.snapshot("graphics")
                receipt = self.media.renderer()
                if receipt.effective is not None:
                    visual = VisualSettings.model_validate(
                        receipt.effective.model_dump(
                            include=set(VisualSettings.model_fields)
                        )
                    )
            except (OSError, ValidationError, AdapterFaultError, StorePrivacyError):
                available = False
        snapshot = self._selected_snapshot(snapshot)
        available = available and snapshot is not None
        if snapshot != self.seen:
            revision += 1
            self.seen = snapshot
        effect = snapshot.effect if snapshot is not None else None
        safe = (
            effect
            if isinstance(effect, (GraphicsEffect, HudEffect, SfxEffect))
            else None
        )
        ack = self.effects.last_ack
        if (
            snapshot is None
            or ack is None
            or snapshot.owner != ack.owner
            or snapshot.revision != ack.revision
        ):
            ack = None
        previous = (
            self.effects.previous.effect if self.effects.previous is not None else None
        )
        return OwnerState(
            origin="controller",
            epoch=epoch,
            revision=revision,
            health="fresh" if available else "unavailable",
            applied=safe,
            previous=previous
            if isinstance(previous, (GraphicsEffect, HudEffect, SfxEffect))
            else None,
            saved=saved,
            framing=framing.policy.preset if framing else None,
            receipt=ack,
            visual=visual,
            visual_available=available,
            framing_available=available,
            reason="observed" if available else "unavailable",
        )

    def _selected_snapshot(
        self, graphics: PropertyState | None
    ) -> PropertyState | None:
        if self.effects.current is None or self.effects.current.resource == "graphics":
            return graphics
        try:
            return self.media.snapshot(self.effects.current.resource)
        except (OSError, ValidationError, AdapterFaultError, StorePrivacyError):
            return None
