"""Explicit opt-in private production lifetime; no device/provider startup."""

from contextlib import ExitStack
from pathlib import Path
from threading import Thread
from types import TracebackType
from typing import Annotated, Self, final

from pydantic import Field, SecretStr, model_validator

from .effect_contracts import Contract, Identifier
from .production_dispatch import ProductionDispatch, SourceBinding
from .production_http import OwnerHttpServer
from .production_mailbox import PrivateMailbox
from .production_media import ProductionMedia
from .production_media_channel import MediaBinding
from .production_runtime import ProductionRuntime
from .reaction_contracts import ReactionPack
from .reaction_scheduler import ReactionScheduler
from .reaction_store import ReactionStore
from .reaction_types import HostClock


class ProductionSettings(Contract):
    """Operator-local opt-in configuration; never a tool argument."""

    mailbox: Path
    state: Path
    actor_id: Identifier
    packs: Annotated[tuple[ReactionPack, ...], Field(max_length=32)] = ()
    sfx_enabled: bool = False
    remote_source: SourceBinding | None = None
    local_source: SourceBinding | None = None
    studio_directory: Path | None = None
    http_bootstrap: SecretStr | None = None
    http_port: int = Field(default=0, ge=0, le=65535)

    @model_validator(mode="after")
    def unique_packs(self) -> Self:
        """Reject ambiguous configured names before constructing any owner."""
        if len({pack.pack_id for pack in self.packs}) != len(self.packs):
            message = "duplicate curated pack identifier"
            raise ValueError(message)
        return self


@final
class ProductionLifetime:
    """Own mailbox lock, SQLite scheduler, optional loopback API and teardown."""

    def __init__(self, settings: ProductionSettings) -> None:
        """Acquire only configured private local resources, never create an engine."""
        with ExitStack() as resources:
            self.resources = resources
            clock = HostClock()
            mailbox = self.resources.enter_context(PrivateMailbox(settings.mailbox))
            store = self.resources.enter_context(
                ReactionStore(settings.state / "reactions.sqlite")
            )
            media = ProductionMedia(
                mailbox, clock, MediaBinding(settings.actor_id, settings.sfx_enabled)
            )
            scheduler = ReactionScheduler(store, media, clock)
            self.runtime = ProductionRuntime(media, scheduler, clock)
            _ = self.resources.callback(self.runtime.close)
            self.dispatch = ProductionDispatch(
                self.runtime,
                settings.packs,
                settings.remote_source,
                settings.local_source,
            )
            self.http: OwnerHttpServer | None = None
            if settings.http_bootstrap is not None:
                self.http = OwnerHttpServer(
                    self.runtime,
                    settings.http_bootstrap,
                    settings.http_port,
                    studio_directory=settings.studio_directory,
                )
                thread = Thread(
                    target=self.http.serve_forever, name="production-owner-http"
                )
                thread.start()
                _ = self.resources.callback(self.http.server_close)
                _ = self.resources.callback(thread.join)
                _ = self.resources.callback(self.http.shutdown)
            self.resources = resources.pop_all()

    def __enter__(self) -> Self:
        """Retain exclusive ownership until all transports are closed."""
        return self

    def __exit__(
        self,
        _kind: type[BaseException] | None,
        _value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Stop HTTP first, consume scheduled work, then release file owners."""
        self.resources.close()
