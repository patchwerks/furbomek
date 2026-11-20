"""Fixed-name private owner preset persistence, with no activation on load."""

import os
import stat
from contextlib import suppress
from pathlib import Path
from typing import final
from uuid import uuid4

from .production_http_models import OwnerSaved
from .reaction_types import StorePrivacyError

FILE_MODE = 0o600
MAX_BYTES = 65536


@final
class SavedPreset:
    """Use the already validated scheduler directory; reject replacement links."""

    def __init__(self, directory: Path) -> None:
        """Keep only an operator-configured path, never a request path."""
        self.directory = directory

    def load(self) -> OwnerSaved | None:
        """Load typed configuration without granting admission or dispatching."""
        try:
            descriptor = os.open(
                self.directory / "owner-preset.json",
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            )
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor, "rb") as file:
            info = os.fstat(file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != FILE_MODE
                or info.st_nlink != 1
            ):
                raise StorePrivacyError(str(self.directory))
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise StorePrivacyError(str(self.directory))
        return OwnerSaved.model_validate_json(raw)

    def save(self, preset: OwnerSaved) -> None:
        """Atomically persist only the bounded typed preset at a fixed filename."""
        raw = preset.model_dump_json().encode()
        if len(raw) > MAX_BYTES:
            raise StorePrivacyError(str(self.directory))
        temporary = self.directory / f".preset-{uuid4().hex}"
        try:
            with os.fdopen(
                os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                ),
                "wb",
            ) as file:
                _ = file.write(raw)
                file.flush()
                os.fsync(file.fileno())
            _ = temporary.replace(self.directory / "owner-preset.json")
        finally:
            with suppress(FileNotFoundError):
                temporary.unlink()
